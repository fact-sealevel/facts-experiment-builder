from traitlets.config import Config


def main():
    import IPython

    c = Config()
    c.InteractiveShellApp.extensions = ["autoreload"]
    c.InteractiveShellApp.exec_lines = ["%autoreload 2"]
    IPython.start_ipython(argv=[], config=c)
