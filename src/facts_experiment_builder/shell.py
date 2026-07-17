from traitlets.config import Config
"""For development purposes, to easily enter an ipython shell with autoreload."""

def main():
    import IPython

    c = Config()
    c.InteractiveShellApp.extensions = ["autoreload"]
    c.InteractiveShellApp.exec_lines = ["%autoreload 2"]
    IPython.start_ipython(argv=[], config=c)
