import procrastinate

procrastinate_app = procrastinate.App(
    connector=procrastinate.PsycopgConnector(),
    import_paths=["app.tasks"],
)
