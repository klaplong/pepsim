from collections import deque as queue
# TODO: 'log' function wrapper.


class MachineControl:
    def __init__(self, debug=False):
        # Implementation choice: simple queued execution.
        self.machines = queue()

        self.event_reactions = {}
        self.machine_reactions = {}

        self.event_buss = queue()

        self.ctx = None

        self.debug = debug

    def start_machine(self, machine_cls, ctx, *args, **kwargs):
        machine = machine_cls(self, ctx, *args, **kwargs)

        self.machines.append(machine)

        self.add_event_reaction('start', machine, machine.init_state)

        self.emit(Event('start', ctx, destination=machine))

        return machine

    def add_event_reaction(self, typ, reactor, state):
        if typ not in self.event_reactions:
            self.event_reactions[typ] = {}

        self.event_reactions[typ][reactor] = state

    def add_machine_reaction(self, typ, emitter, reactor, state):
        index = (typ, emitter)

        if index not in self.machine_reactions:
            self.machine_reactions[index] = {}

        self.machine_reactions[index][reactor] = state

    def emit(self, event):
        self.event_buss.append(event)

    def run(self, machine_cls, *args, **kwargs):
        self.ctx = StateMachine(self, None)
        self.start_machine(machine_cls, self.ctx, *args, **kwargs)

        while self.cycle():
            pass

    def cycle(self):
        while self.distribute_events():
            pass

        if self.debug:
            print('machines:')
            print(self.machines)

        try:
            machine = self.machines.popleft()
        except IndexError:
            return False

        self.machines.append(machine)
        machine.cycle()

        return True

    def distribute_events(self):
        try:
            event = self.event_buss.popleft()
        except IndexError:
            return False

        if self.debug:
            print('distributing %s' % (event))

        if event.typ in self.event_reactions:
            self.distribute_reactors(self.event_reactions[event.typ], event)

        index = (event.typ, event.emitter)
        if index in self.machine_reactions:
            self.distribute_reactors(self.machine_reactions[index], event)

        return True

    def distribute_reactors(self, reactors, event):
        if event.destination is not None:
            if event.destination in reactors:
                if self.debug:
                    print('to %s' % (event.destination))

                event.destination.inbox.append(
                    Event.with_state(event, reactors[event.destination]))

        else:
            for reactor, state in reactors.items():
                if self.debug:
                    print('to %s' % (reactor))

                reactor.inbox.append(
                    Event.with_state(event, state))

    def halt(self, machine):
        self.machines.remove(machine)


class Event:
    def __init__(self, typ, emitter, value=None, destination=None, ack=False):
        self.typ = typ
        self.value = value
        self.emitter = emitter
        self.destination = destination
        self.ack = ack

        self.state = None

    def __repr__(self):
        return '<Event:typ=%s,emitter=%s,destination=%s,ack=%s>' % (
            self.typ, self.emitter, self.destination, self.ack)

    @classmethod
    def with_state(cls, event, state):
        event_prime = cls(event.typ, event.emitter, event.value,
                          event.destination, event.ack)
        event_prime.state = state
        return event_prime


class StateMachine:
    def __init__(self, ctl, ctx):
        self.ctl = ctl
        self.ctx = ctx

        self.current_state = self.listen

        self.inbox = queue()
        self.event = None

        self.init_state = self.halt

    def cycle(self):
        if self.ctl.debug:
            print('cycling state %s' % (self.current_state))

        new_state = self.current_state()

        if new_state is None:
            new_state = self.listen

        self.current_state = new_state

    def emit(self, typ, value=None):
        self.emit_to(None, typ, value=value)

    def emit_to(self, destination, typ, value=None, ack_state=None):
        self.ctl.emit(Event(typ, self, value=value, destination=destination,
                            ack=ack_state is not None))

        if ack_state is not None:
            self.when_machine_emits(typ + '_ack', destination, ack_state)

    def start_machine(self, machine_cls, *args, **kwargs):
        return self.ctl.start_machine(machine_cls, self, *args, **kwargs)

    def when_machine_emits(self, typ, machine, state):
        self.ctl.add_machine_reaction(typ, machine, self, state)

    def when(self, typ, state):
        self.ctl.add_event_reaction(typ, self, state)

    def listen(self):
        if self.ctl.debug:
            print(str(self) + ' is listening, inbox:')
            print(self.inbox)

        try:
            self.event = self.inbox.popleft()
        except IndexError:
            return

        if self.event.ack:
            self.emit_to(self.event.emitter, self.event.typ + '_ack',
                         value=self.event.value)

        if self.ctl.debug:
            print('going to state ' + str(self.event.state))

        return self.event.state

    def halt(self):
        if self.ctl.debug:
            print(str(self) + ' is halting')

        self.ctl.halt(self)
