"""
LinuxNLearn – application entry point.

Usage
-----
  python run.py

ngrok support
-------------
Set NGROK_AUTH_TOKEN (or NGROK_AUTHTOKEN) in your .env file to expose the app
publicly via an ngrok HTTPS tunnel. The public URL is printed to the console on
startup.

Optionally set NGROK_DOMAIN to a static domain from your ngrok dashboard
(e.g. abc123.ngrok-free.app) so the URL never changes between restarts.

Environment variables (all set in .env)
---------------------------------------
  PORT              – local port to listen on              (default: 5000)
  DEBUG             – enable Flask debug mode              (default: false)
    NGROK_AUTH_TOKEN  – your ngrok authtoken (preferred)
    NGROK_AUTHTOKEN   – alternate ngrok authtoken variable name
    NGROK_API_KEY     – optional for ngrok API usage (not tunnel auth)
  NGROK_DOMAIN      – optional static ngrok domain
"""

import sys

import config


def _start_ngrok(port):
    """Start a pyngrok tunnel and return the public URL, or None on failure."""
    try:
        from pyngrok import conf, ngrok

        conf.get_default().auth_token = config.NGROK_AUTH_TOKEN

        kwargs = {}
        if config.NGROK_DOMAIN:
            kwargs["domain"] = config.NGROK_DOMAIN

        tunnel = ngrok.connect(port, "http", **kwargs)
        return tunnel.public_url
    except ImportError:
        print("[ngrok] pyngrok is not installed. Run: pip install pyngrok", file=sys.stderr)
        return None
    except Exception as exc:  # noqa: BLE001
        print(f"[ngrok] Could not start tunnel: {exc}", file=sys.stderr)
        return None


def main():
    from app import app

    port = config.PORT
    public_url = None

    if config.NGROK_AUTH_TOKEN and config.NGROK_AUTH_TOKEN.startswith("ak_"):
        print("[ngrok] NGROK_AUTH_TOKEN appears to be an API key (starts with 'ak_').")
        print("[ngrok] Use your ngrok authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken")
        print(f"\nStarting locally on http://localhost:{port}\n")
    elif config.NGROK_AUTH_TOKEN:
        public_url = _start_ngrok(port)
        if public_url:
            print("\n" + "=" * 54)
            print("  🌐  ngrok tunnel active!")
            print(f"  Public URL : {public_url}")
            print(f"  Local URL  : http://localhost:{port}")
            print("=" * 54 + "\n")
        else:
            print(f"\nStarting locally on http://localhost:{port}\n")
    elif config.NGROK_API_KEY:
        print("[ngrok] NGROK_API_KEY is set, but tunnel auth requires NGROK_AUTH_TOKEN/NGROK_AUTHTOKEN.")
        print("[ngrok] Set your authtoken in .env to enable public tunnel startup.")
        print(f"\nStarting locally on http://localhost:{port}\n")
    else:
        print(f"\nStarting LinuxNLearn on http://localhost:{port}")
        print("Tip: set NGROK_AUTH_TOKEN in .env to expose publicly.\n")

    app.run(debug=config.DEBUG, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
