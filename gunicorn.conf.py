# Default gunicorn config file. https://docs.gunicorn.org/en/stable/configure.html
import gunicorn

# Override the `Server: gunicorn/x.y.z` version header in responses.
gunicorn.SERVER_SOFTWARE = "lite-hmrc"

accesslog = "-"
errorlog = "-"
