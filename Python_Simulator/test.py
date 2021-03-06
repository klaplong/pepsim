from simulator import MachineControl, StateMachine


class TestA(StateMachine):
    def __init__(self, ctl, ctx, n):
        super().__init__(ctl, ctx)

        self.init_state = self.init
        self.n = n

    def __repr__(self):
        return '<A:n=%d>' % (self.n)

    def init(self):
        self.ms = []
        self.i = 0
        self.j = 0
        return self.start_machines

    def start_machines(self):
        if self.i < self.n:
            m = self.start_machine(TestB, i=self.i + 1)
            self.ms.append(m)
            self.when_machine_emits('done', m, self.m_done)

            print('created machine %d' % (self.i + 1))

            self.i += 1
            return self.start_machines

        self.emit('run')

    def m_done(self):
        print('machine %d is done' % (self.event.value))

        self.n -= 1

        print('%d left to be done' % (self.n))

        if self.n == 0:
            return self.halt


class TestB(StateMachine):
    def __init__(self, ctl, ctx, i):
        super().__init__(ctl, ctx)

        self.init_state = self.init
        self.i = i

    def __repr__(self):
        return '<B:i=%d>' % (self.i)

    def init(self):
        self.when('run', self.prnt)

    def prnt(self):
        print('i am machine %d' % (self.i))
        self.emit_to(self.ctx, 'done', value=self.i)


if __name__ == '__main__':
    ctl = MachineControl(debug=True, step=True)
    ctl.run(TestA, 2)
