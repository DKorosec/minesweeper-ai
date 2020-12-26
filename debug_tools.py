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
