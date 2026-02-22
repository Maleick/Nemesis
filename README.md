<p align="center">
    <img src="docs/images/nemesis-light.png" alt="Nemesis" style="width: 800px;" />
</p>
<hr />

<p align="center">
<img src="https://img.shields.io/badge/version-2.0.0-blue" alt="version 2.0.0"/>
<a href="https://join.slack.com/t/bloodhoundhq/shared_invite/zt-1tgq6ojd2-ixpx5nz9Wjtbhc3i8AVAWw">
    <img src="https://img.shields.io/badge/Slack-%23nemesis—chat-blueviolet?logo=slack" alt="Slack"/>
</a>
<a href="https://twitter.com/tifkin_">
    <img src="https://img.shields.io/twitter/follow/tifkin_?style=social"
      alt="@tifkin_ on Twitter"/></a>
<a href="https://twitter.com/harmj0y">
    <img src="https://img.shields.io/twitter/follow/harmj0y?style=social"
      alt="@harmj0y on Twitter"/></a>
<a href="https://twitter.com/0xdab0">
    <img src="https://img.shields.io/twitter/follow/0xdab0?style=social"
      alt="@0xdab0 on Twitter"/></a>
<a href="https://github.com/specterops#nemesis">
    <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fspecterops%2F.github%2Fmain%2Fconfig%2Fshield.json&style=flat"
      alt="Sponsored by SpecterOps"/>
</a>
</p>
<hr />

# Overview

Nemesis is an open-source, centralized data processing platform that ingests, enriches, and allows collaborative analysis (with humans and AI) of files collected during offensive security assessments.


Nemesis 2.0 is built on [Docker](https://www.docker.com/) with heavy [Dapr integration](https://dapr.io/), our goal with Nemesis was to create a centralized file processing platform that functions as an "offensive VirusTotal".

_Note: the previous Nemesis 1.0.1 code base has been preserved [as a branch](https://github.com/SpecterOps/Nemesis/tree/nemesis-1.0.1)_

## Setup / Installation
Follow the [quickstart guide](docs/quickstart.md).


## Usage
See the [Nemesis Usage Guide](docs/usage_guide.md).

## Operational Notes

### LLM provider authentication options (Codex + Gemini)

When the `--llm` profile is enabled, Nemesis routes model calls through LiteLLM (`infra/litellm/config.yml`).
For both Codex and Gemini, you can choose either interactive OAuth credentials or non-interactive credentials for automation.

| Provider | Auth option | Best for | Notes |
| --- | --- | --- | --- |
| Codex (OpenAI via LiteLLM) | OAuth user/session token | Local interactive testing | Fast to get started for personal/dev usage; token refresh can be required. |
| Codex (OpenAI via LiteLLM) | API key or service credential | CI, servers, unattended runs | Recommended for stability in automation and scheduled jobs. |
| Gemini (Google via LiteLLM) | OAuth user/session token | Local interactive testing | Useful for developer workflows; avoid for unattended runtime. |
| Gemini (Google via LiteLLM) | API key or service credential | CI, servers, unattended runs | Recommended for fork CI and long-running deployments. |

Credential handling guidance:
- Store secrets in `.env` (gitignored) or your runtime secret manager, never in git-tracked files.
- Reference those secrets from `infra/litellm/config.yml`.
- Keep at least one configured model named `default` for agents.

#### Quick switch snippets (Codex vs Gemini)

Choose one mode at a time, then restart with `./tools/nemesis-ctl.sh start prod --llm`.

Codex OAuth mode (`.env`):

```dotenv
LLM_AUTH_MODE=codex_oauth
CODEX_AUTH_EXPERIMENTAL=true
CODEX_AUTH_PROFILE_MOUNT_SOURCE=$HOME/.codex/auth.json
CODEX_AUTH_PROFILE_PATH=/run/secrets/codex-auth-profile.json
CODEX_AUTH_PROFILE_NAME=openai-codex:default
```

Gemini via Google AI Studio (`.env`):

```dotenv
LLM_AUTH_MODE=official_key
GEMINI_API_KEY=your-gemini-api-key
```

Gemini via Google AI Studio (`compose.yaml`, `litellm.environment` add):

```yaml
- GEMINI_API_KEY=${GEMINI_API_KEY:-}
```

Gemini via Google AI Studio (`infra/litellm/config.yml`, set `default`):

```yaml
model_list:
  - model_name: default
    litellm_params:
      model: gemini/gemini-2.5-flash
      api_key: os.environ/GEMINI_API_KEY
```

Gemini via Vertex AI (`.env`):

```dotenv
LLM_AUTH_MODE=official_key
VERTEX_PROJECT=your-gcp-project-id
VERTEX_LOCATION=us-central1
VERTEX_CREDENTIALS_FILE=/absolute/path/to/service-account.json
```

Gemini via Vertex AI (`compose.yaml`, `litellm.environment` add):

```yaml
- VERTEX_PROJECT=${VERTEX_PROJECT:-}
- VERTEX_LOCATION=${VERTEX_LOCATION:-}
```

Gemini via Vertex AI (`compose.yaml`, `litellm.volumes` add):

```yaml
- ${VERTEX_CREDENTIALS_FILE}:/run/secrets/vertex-service-account.json:ro
```

Gemini via Vertex AI (`infra/litellm/config.yml`, set `default`):

```yaml
model_list:
  - model_name: default
    litellm_params:
      model: vertex_ai/gemini-2.5-pro
      vertex_project: your-gcp-project-id
      vertex_location: us-central1
      vertex_credentials: /run/secrets/vertex-service-account.json
```

### Chatbot MCP credential preflight

When the `--llm` profile is enabled, the `agents` service starts the chatbot MCP server (`genai-toolbox`) at startup.
Nemesis now runs a startup preflight that validates the `chatbot_readonly` database login before launching MCP.
If `CHATBOT_DB_PASSWORD` in `.env` drifts from the actual Postgres role password, startup logs include an explicit preflight failure with remediation guidance.

If you rotate `CHATBOT_DB_PASSWORD` after initial database bootstrap, sync the role password and restart chatbot path services:

```bash
cd /path/to/Nemesis

POSTGRES_USER=$(awk -F= '/^POSTGRES_USER=/{gsub(/"/,"",$2);print $2}' .env)
POSTGRES_PASSWORD=$(awk -F= '/^POSTGRES_PASSWORD=/{gsub(/"/,"",$2);print $2}' .env)
POSTGRES_DB=$(awk -F= '/^POSTGRES_DB=/{gsub(/"/,"",$2);print $2}' .env)
CHATBOT_DB_PASSWORD=$(awk -F= '/^CHATBOT_DB_PASSWORD=/{gsub(/"/,"",$2);print $2}' .env)

docker compose --profile llm -f compose.yaml exec -T postgres sh -lc \
  "PGPASSWORD='${POSTGRES_PASSWORD}' psql -h postgres -U '${POSTGRES_USER}' -d '${POSTGRES_DB}' -v ON_ERROR_STOP=1 -c \"ALTER ROLE chatbot_readonly WITH PASSWORD '${CHATBOT_DB_PASSWORD}';\""

docker compose --profile llm -f compose.yaml up -d agents agents-dapr
```


## Additional Information
Blog Posts:

| Title                                                                                                                                                            | Nemesis Version | Date         |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | ------------ |
| [*Nemesis 2.0*](https://specterops.io/blog/2025/08/05/nemesis-2-0/)                                                                                              | v2.0            | Aug 5, 2025  |
| [*Nemesis 1.0.0*](https://posts.specterops.io/nemesis-1-0-0-8c6b745dc7c5)                                                                                        | v1.0            | Apr 25, 2024 |
| [*Summoning RAGnarok With Your Nemesis*](https://posts.specterops.io/summoning-ragnarok-with-your-nemesis-7c4f0577c93b)                                          | v1.0            | Mar 13, 2024 |
| [*Shadow Wizard Registry Gang: Structured Registry Querying*](https://posts.specterops.io/shadow-wizard-registry-gang-structured-registry-querying-9a2fab62a26f) | v1.0            | Sep 5, 2023  |
| [*Hacking With Your Nemesis*](https://posts.specterops.io/hacking-with-your-nemesis-7861f75fcab4)                                                                | v1.0            | Aug 9, 2023  |
| [*Challenges In Post-Exploitation Workflows*](https://posts.specterops.io/challenges-in-post-exploitation-workflows-2b3469810fe9)                                | v1.0            | Aug 2, 2023  |
| [*On (Structured) Data*](https://posts.specterops.io/on-structured-data-707b7d9876c6)                                                                            | v1.0            | Jul 26, 2023 |


Presentations:

| Title                                                                      | Date         |
|----------------------------------------------------------------------------|--------------|
| OffensiveX 2025                                                            | Jun 19, 2025 |
| [*x33fcon 2025*](https://www.youtube.com/watch?v=RjLqfhQGUnE)              | Jun 13, 2025 |
| [*SAINTCON 2023*](https://www.youtube.com/watch?v=0q9u2hDcpIo)             | Oct 24, 2023 |
| [*BSidesAugusta 2023*](https://www.youtube.com/watch?v=Ug9r7lCF_FA)        | Oct 7, 2023  |
| [*44CON 2023*](https://www.youtube.com/watch?v=tjPTLBGI7K8)                | Sep 15, 2023 |
| [*BlackHat Arsenal USA 2023*](https://www.youtube.com/watch?v=Ms3o8n6aS0c) | Sep 15, 2023 |


## Acknowledgments

Nemesis is built on large chunk of other people's work. Throughout the codebase we've provided citations, references, and applicable licenses for anything used or adapted from public sources. If we're forgotten proper credit anywhere, please let us know or submit a pull request!

We also want to acknowledge Evan McBroom, Hope Walker, and Carlo Alcantara from [SpecterOps](https://specterops.io/) for their help with the initial Nemesis concept and amazing feedback throughout the development process. Also thanks to [Matt Ehrnschwender](https://twitter.com/M_alphaaa) for tons of k3s and GitHub workflow help in Nemesis 1.0!

And finally, shout out to OpenAI and Claude for helping with this rewrite.
