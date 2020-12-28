from timeit import default_timer as timer


d = dict()
d['?'] = '\033[42m'
d['!'] = '\033[41m'
d[0] = '\033[7m'
d[1] = '\033[34m'
d[2] = '\033[32m'
d[3] = '\033[91m'
d[4] = '\033[35m'
d[5] = '\033[33m'


def debug_print_state(state):
    for row in state:
        print(''.join([d.get(r, '') + '['+str(r)+']' +
                       '\033[0m' for r in row]))
    print('\n')


class benchmark():
    """
    # https://stackoverflow.com/questions/7370801/how-to-measure-elapsed-time-in-python
    with benchmark("Test 1+1") as b:
        1+1
    print(b.time)
    =>
    Test 1+1 : 7.05e-07 seconds
    7.05233786763e-07
    """

    def __init__(self, msg, fmt="%0.3g"):
        self.msg = msg
        self.fmt = fmt

    def __enter__(self):
        self.start = timer()
        return self

    def __exit__(self, *args):
        t = timer() - self.start
        print(("%s : " + self.fmt + " seconds") % (self.msg, t))
        self.time = t
