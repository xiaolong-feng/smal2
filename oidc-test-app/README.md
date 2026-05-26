# OIDC Test App

这个最小 OIDC RP 测试应用用于验证：

```text
OIDC 应用 -> SATOSA OIDC Frontend -> SATOSA SAML Backend -> 外部 SAML IdP
```

应用会完成 OIDC authorization code 登录，并在回调页面展示：

- token response
- id_token claims
- userinfo response
- `id_token.sub` 与 `userinfo.sub` 是否一致

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `OIDC_ISSUER` | `https://10.10.0.26` | SATOSA OIDC issuer |
| `OIDC_DISCOVERY_URL` | `${OIDC_ISSUER}/.well-known/openid-configuration` | 测试应用实际访问的 discovery 地址 |
| `OIDC_CLIENT_ID` | `oidc-test-app` | 测试应用 client id |
| `OIDC_CLIENT_SECRET` | `test-secret` | 测试应用 client secret |
| `OIDC_REDIRECT_URI` | `http://localhost:18080/callback` | OIDC 回调地址 |
| `OIDC_SCOPE` | `openid profile email` | 登录请求 scope |
| `OIDC_VERIFY_TLS` | `false` | 是否校验 SATOSA TLS 证书 |

如果 SATOSA discovery 返回的 endpoint 不适合容器访问，可以用下面变量覆盖：

- `OIDC_AUTHORIZATION_ENDPOINT`
- `OIDC_TOKEN_ENDPOINT`
- `OIDC_USERINFO_ENDPOINT`

在 Docker Compose 里默认让测试应用通过 `https://satosa` 访问 discovery、token、userinfo，这样容器内部不依赖宿主机 IP 路由；浏览器跳转仍使用 SATOSA metadata 里发布的公网 authorization endpoint。

## 启动

在项目根目录运行：

```bash
docker compose -f docker-compose.yml -f docker-compose.oidc-test.yml up --build
```

访问：

```text
http://localhost:18080
```

## SATOSA 侧启用方式

本目录只提供 OIDC 测试应用。要跑通完整协议转换，还需要让 SATOSA 启用 OIDC frontend：

```yaml
FRONTEND_MODULES:
  - "/opt/satosa/plugins/frontends/oidc_frontend.yaml"

BACKEND_MODULES:
  - "/opt/satosa/plugins/backends/saml2_backend.yaml"
```

测试客户端已经放在：

```text
etc/oidc_clients.json
```

## 成功判断

页面显示“登录成功”，并且能看到：

- `id_token`
- `access_token`
- `ID Token Claims`
- `UserInfo`
- `id_token.sub` 与 `userinfo.sub` 一致

这说明不仅协议转换链路跑通了，用户信息也从上游 SAML IdP 转换到了 OIDC 应用侧。
