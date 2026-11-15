"""Drive a complete bounded administration cycle without changing game state."""


def run_admin_cycle(admin):
    # Seven ordinary callbacks cover every scheduled domain once. The fixture's
    # turn, permissions, pending requests and native acknowledgement stay intact.
    for _ in range(7):
        admin.Run()
