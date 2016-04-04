class ConfigEditor(object):
    def __init__(self, foo=1, bar=2):
        self.foo = foo
        self.bar = bar
        print "enter XMLEditor"
        super(ConfigEditor, self).__init__()
        print "exit XMLEditor"

class RefiningMixin(object):
    def __init__(self):
        print "enter RefiningSector"
        self.baz = self.foo * self.bar
        super(RefiningMixin, self).__init__()
        print "exit RefiningSector"

class BiofuelMixin(object):
    def __init__(self):
        print "enter BiofuelMixin"
        self.buz = self.foo * self.bar + 10
        super(BiofuelMixin, self).__init__()
        print "exit BiofuelMixin"

class MyScenario(ConfigEditor, BiofuelMixin, RefiningMixin):
    def __init__(self, *args, **kwargs):
        print 'enter MyScenario'
        super(MyScenario, self).__init__(*args, **kwargs)
        print 'exit MyScenario'

x = MyScenario(foo=4, bar=3)
print "baz = %s" % x.baz
print "buz = %s" % x.buz
