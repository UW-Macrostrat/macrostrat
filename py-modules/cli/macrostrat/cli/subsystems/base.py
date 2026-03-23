from macrostrat.app_frame import Application, Subsystem, CommandBase


class MacrostratSubsystem(Subsystem):
    def __init__(self, app: Application):
        self.app = app
        self.settings = app.settings

    def control_command(self, **kwargs):
        return CommandBase(**kwargs)
