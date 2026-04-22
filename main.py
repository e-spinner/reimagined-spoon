from ai_final_project.main import main as app_main


def main() -> None:
    # Keep the repository-root launcher tiny: delegate to package entrypoint.
    # `SystemExit` forwards the returned exit code to the shell.
    raise SystemExit(app_main())


if __name__ == "__main__":
    main()
