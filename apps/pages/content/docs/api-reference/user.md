---
title: User API
description: Verify a TastefulKit API key and check which account it belongs to.
---

# Check your API access

API and MCP access to design metadata and screenshots is free. Create an account
and generate an API key in [Account settings](/settings). DESIGN.md guide text
requires an active [$10/month membership](/pricing/).


Use `GET /api/user` to verify a key before searching the catalogue. It returns the account associated with the supplied key, not any other user's account.

```bash
curl 'https://tastefulkit.com/api/user' \
  -H "Authorization: Bearer $TASTEFULKIT_API_KEY"
```

An example response is shown below. The email is fictional; your response contains your own account's email.

```json
{
  "email": "you@example.com",
  "profile": {
    "state": "signed_up"
  }
}
```

The response does not include your API key or administrator flags. A successful HTTP **200** confirms the key works. HTTP **401** means you should check the [authentication steps](/docs/api-reference/introduction/).

Next, [search for designs](/docs/api-reference/design-library/).
