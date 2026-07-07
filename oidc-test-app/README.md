# OIDC Test App

This small OIDC relying party verifies this flow:

```text
OIDC app -> SATOSA OIDC Frontend -> SATOSA SAML Backend -> external SAML IdP
```

## Environment

| Variable | Default | Description |
|---|---|---|
| `OIDC_ISSUER` | `https://202.122.38.207:8443` | Public SATOSA OIDC issuer |
| `OIDC_DISCOVERY_URL` | `${OIDC_ISSUER}/.well-known/openid-configuration` | Discovery URL used by the app |
| `OIDC_CLIENT_ID` | `oidc-test-app` | Test client id |
| `OIDC_CLIENT_SECRET` | `test-secret` | Test client secret |
| `OIDC_REDIRECT_URI` | `http://202.122.38.207:18080/callback` | Browser callback URL |
| `OIDC_SCOPE` | `openid profile email` | Requested scope |
| `OIDC_VERIFY_TLS` | `false` | Whether to verify the SATOSA TLS certificate |

The Docker Compose test setup makes the container call SATOSA through
`https://satosa` for discovery, token, and userinfo endpoints, while the browser
uses the public server IP published in SATOSA metadata.

## Start

Run from the project root:

```bash
docker compose -f docker-compose.yml -f docker-compose.oidc-test.yml up --build
```

Open:

```text
http://202.122.38.207:18080
```

## Success Criteria

After login, the page should show:

- token response
- ID token claims
- UserInfo response
- whether `id_token.sub` and `userinfo.sub` match
