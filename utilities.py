import shutil
import sys
import functools
from urllib.parse import urlparse


def parse_filename(link: str) -> str:
    return urlparse(link).path.split('/')[-1]


def parse_extension(link: str) -> str:
    return '.' + parse_filename(link).split('.')[-1]


def progress_bar(iteration, total, prefix='', suffix=''):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
    """
    terminal_width = shutil.get_terminal_size()[0]
    bar_length = terminal_width - len(prefix) - len(suffix) - 13

    if total > 0:
        filled_length = int(round(bar_length * iteration / float(total)))
        percents = round(100.00 * (iteration / float(total)), 2)
    else:
        filled_length = bar_length
        percents = 100

    print('{} [{:{fill}<{width}}] {:6.2f}% {}'.format(
        prefix, '#' * filled_length, percents, suffix, width=bar_length, fill='-'),
        end='\r', flush=True)
    if iteration == total:
        print()


termcolor = dict(
    BOLD='\033[1m',
    END='\033[0m'
)

class term_str(str):
    def __new__(cls, string):
        return super(term_str, cls).__new__(cls, string)

    def __getattribute__(self, name):
        func = str.__getattribute__(self, name)
        if not callable(func):
            return func

        def callback(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, str):
                return term_str(result)
            return result
        return functools.partial(callback)

    def bold(self):
        return termcolor['BOLD'] + self + termcolor['END']

    def len_special(self):
        """Get length of special terminal characters (usually non-printable)"""
        return sum(self.count(term_chars) * len(term_chars) for term_chars in termcolor.values())

    def __len__(self):
        return len(self) - self.len_special()
