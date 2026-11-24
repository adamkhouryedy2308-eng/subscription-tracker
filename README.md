# SubTrack – Subscription Tracker

A simple web app that helps people keep track of their recurring subscriptions
(Netflix, Spotify, gym, iCloud, …), see how much they really spend, and get
warned before a renewal or a free trial turns into a charge.

**Live on Azure: https://akhouryieu2024ui.z33.web.core.windows.net**
(the first click after a quiet hour can take about a minute: see "Cold starts" below).

Built for **Software Development & DevOps**. Assignment 1 was one Flask app with
SQLite; **Assignment 2** splits it into two services, each with its own SQL Server
database, runs it with Docker Compose, and deploys it to Azure with GitHub Actions.

## The system

```
 browser ── ui/ (static HTML, CSS, JavaScript) ─────────────────────────────┐
     │                                                                      │
     ▼ JSON + login token                                                   ▼ JSON + login token
 Subscriptions service  ◄── GET /subscriptions/active (2 s timeout) ──  Budgets & Alerts service
 accounts, subscriptions,                                               budgets, spending, alerts
 price history, bank import                                                     │
     │                                                                          │
     ▼                                                                          ▼
 subscriptions database (users, subscriptions, price_changes)        budgets database (budgets)
```

| Folder | What it is |
|---|---|
| `services/subscriptions` | Flask JSON service: accounts and login, subscriptions, price history, bank import |
| `services/budgets` | Flask JSON service: budgets, spending per category, alerts; asks Subscriptions for the active subscriptions |
| `services/*/migrations` | numbered SQL files, applied once and in order when the service starts |
| `services/*/openapi.yaml` | every endpoint of the service (OpenAPI 3) |
| `ui/` | the website: plain files, `config.js` says where the services are |
| `tests/test_cross_seam.py` | both real services together, then Subscriptions stopped |
| `db/init.sql` | creates the two databases and one login per service (local only) |
| `system.yaml` | the whole system in one file, checked against the professor's `system.schema.json` |
| `.github/workflows` | `ci.yml` (checks every change) and `cd.yml` (deploys `main` to Azure) |

If Subscriptions is down, Budgets keeps working: the budgets page shows the saved
budgets with "spending unavailable", alerts answer a clear 503, and saving a budget
still works (ADR-6).

## Run it on your laptop (Docker Compose)

You need **Docker Desktop** (on an Apple-chip Mac, switch on "Use Rosetta" in its
settings, because SQL Server has no Apple-chip image).

```bash
cp .env.example .env          # then change every password and the secret key in .env
docker compose up --build
```

Open **http://localhost:8080**, sign up and start adding subscriptions. Compose
starts SQL Server, waits until it is healthy, runs `db/init.sql` once (`db-init`),
then starts the two services, which apply their migrations, and the website:

| What | Address |
|---|---|
| Website | http://localhost:8080 |
| Subscriptions service | http://localhost:8001 (try http://localhost:8001/health) |
| Budgets & Alerts service | http://localhost:8002 |

To see partial failure: `docker compose stop subscriptions`, then reload the
Budgets and Alerts pages; `docker compose start subscriptions` brings it back.
`docker compose down` stops everything and keeps the data; `down -v` also deletes it.

**To try the bank import**, open *Import from bank* and upload
`services/subscriptions/sample_data/bank_statement_example.csv`.

## Run one service on its own

Each service is a normal Python program. It needs a SQL Server database (here the
one from compose) and its settings as environment variables (all listed in
`system.yaml`):

```bash
docker compose up -d db-init          # starts SQL Server and creates the databases and logins
cd services/budgets
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL="mssql://budgets_user:<BUDGETS_DB_PASSWORD from .env>@localhost:1433/budgets"
export SECRET_KEY="<SECRET_KEY from .env>" PORT=8002
export SUBSCRIPTIONS_URL=http://localhost:8001    # optional: without it, spending shows as unavailable
python app.py
```

The Subscriptions service is the same from `services/subscriptions`, with
`subscriptions_user`, the `subscriptions` database and `PORT=8001` (it calls no
other service).

## Run the tests and coverage

The tests use their own databases (`subscriptions_test`, `budgets_test`) in the
compose SQL Server, never the real data. Start it first with `docker compose up -d db-init`.

```bash
cd services/subscriptions && pytest --cov     # unit and endpoint tests + coverage (fails below 70%)
cd services/budgets && pytest --cov           # Subscriptions is replaced by a stub here
pytest                                        # from the repository root: the cross-seam test
```

The cross-seam test starts both real services as two programs, signs up, adds a
subscription and a budget, checks that Budgets gets the spending from Subscriptions
over HTTP, then stops Subscriptions and checks the designed failure (ADR-9).

## How deployment works

```
pull request ──► CI: lint · SAST (Bandit) · SCA (pip-audit) · system.yaml + OpenAPI checks · tests + coverage ≥ 70% · cross-seam test · build images
merge to main ─► CD: the same CI, push images to GHCR (tag = commit SHA) ─► deploy to Azure ─► wait for /health ─► DAST (OWASP ZAP)
```

- **CI** (`.github/workflows/ci.yml`) runs on every push to a branch and every pull
  request. Besides lint and tests it runs two security scans: **SAST** with Bandit
  (our own code) and **SCA** with pip-audit (the libraries we use). The tests run against a throwaway SQL Server container with random
  passwords made for that run; CI never touches Azure.
- **CD** (`.github/workflows/cd.yml`) runs on every push to `main`. It runs the same
  CI first and deploys only if every job passed. It signs in to Azure **without a
  password** (OIDC: Azure trusts GitHub's signed token for this repository's `main`
  branch), points each Container App at its new image, gives it its settings and
  secrets (the database password only as a Container Apps secret), writes
  `ui/config.js` with the services' Azure addresses, uploads `ui/` to the storage
  static website, and waits until both `/health` answer 200 **with this commit's SHA**.
  Then **DAST**: OWASP ZAP's baseline scan looks at the live website and both services
  from the outside (passive, safe on the real system). The services' security headers
  are FAIL rules in `.zap/services.tsv`, and the reports are kept with each run.
- **Migrations** run when a service starts. Each service has at most 1 replica, so
  they never run twice at the same time (ADR-8).
- **Cold starts:** with nobody using it, no container runs and the databases pause
  after an hour, so it costs almost nothing. The first request after that waits for
  the container and the database (about a minute); the services retry the database
  connection and the website shows "starting up" and tries again.

### Azure resources

| Resource | Name | Region |
|---|---|---|
| Resource group | `rg-akhoury-ieu2024` | UK South |
| Storage static website (the UI, the public address) | `akhouryieu2024ui` | UK South |
| SQL server | `akhoury-ieu2024-sql-it` | Italy North (UK South refused new SQL servers, ADR-8) |
| Serverless databases, free offer | `akhoury-ieu2024-subscriptions-db`, `akhoury-ieu2024-budgets-db` | Italy North |
| Container Apps environment | `akhoury-ieu2024-env` | Italy North |
| Container Apps (min 0, max 1 replica) | `akhoury-ieu2024-subscriptions`, `akhoury-ieu2024-budgets` | Italy North |
| Managed identity for the pipeline | `akhoury-ieu2024-github` | Italy North |
| Log Analytics workspace (the services' logs; made with the environment, free up to 5 GB a month) | `workspace-rgakhouryieu2024relf` | Italy North |
| Images | `ghcr.io/adamkhouryedy2308-eng/subtrack-subscriptions`, `…/subtrack-budgets` | GitHub |

### Reproduce the initial Azure setup (once, by hand)

Done once from a laptop with `az`, `gh` and Docker, **in Bash** (type `bash` first on
a Mac: zsh changes `$REPO:ref` in the federated credential). No password is written
anywhere: each one is made with `openssl rand` into a shell variable, used, and
stored only as a GitHub secret. After this, only the pipeline changes Azure.

**1. Subscription and region** (Azure for Students allows five regions; check yours with `az policy assignment list`)

```bash
az login
az account set --subscription "Azure for Students"
PREFIX=akhoury-ieu2024
RG=rg-$PREFIX
LOCATION=uksouth          # resource group and UI
SQL_LOCATION=italynorth   # SQL server: UK South refused new SQL servers
APP_LOCATION=italynorth   # Container Apps next to their databases
```

**2. Providers and resource group**

```bash
for p in Microsoft.App Microsoft.OperationalInsights Microsoft.Sql Microsoft.Storage Microsoft.ManagedIdentity; do az provider register --namespace $p; done
az group create --name $RG --location $LOCATION
```

**3. The UI: a storage static website**

```bash
UI_STORAGE=akhouryieu2024ui
az storage account create --name $UI_STORAGE --resource-group $RG --location $LOCATION --sku Standard_LRS --kind StorageV2
az storage blob service-properties update --account-name $UI_STORAGE --static-website --index-document index.html
az storage account show --name $UI_STORAGE --resource-group $RG --query primaryEndpoints.web -o tsv   # the public address
```

**4. SQL server, two serverless databases (free offer) and one contained user per database**

```bash
SQL_SERVER=$PREFIX-sql-it
SQL_ADMIN=subtrackadmin
SQL_ADMIN_PASSWORD="Adm$(openssl rand -hex 16)9"
az sql server create --name $SQL_SERVER --resource-group $RG --location $SQL_LOCATION --admin-user $SQL_ADMIN --admin-password "$SQL_ADMIN_PASSWORD"
az sql server firewall-rule create --resource-group $RG --server $SQL_SERVER --name AllowAzureServices --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0
for svc in subscriptions budgets; do az sql db create --resource-group $RG --server $SQL_SERVER --name $PREFIX-$svc-db --edition GeneralPurpose --compute-model Serverless --family Gen5 --min-capacity 0.5 --capacity 1 --backup-storage-redundancy Local --use-free-limit true --free-limit-exhaustion-behavior AutoPause; done

# Open the firewall to this laptop only while creating the users.
MY_IP=$(curl -s https://api.ipify.org)
az sql server firewall-rule create --resource-group $RG --server $SQL_SERVER --name MyLaptop --start-ip-address $MY_IP --end-ip-address $MY_IP
AZ_SUBSCRIPTIONS_DB_PASSWORD="Sub$(openssl rand -hex 16)7"
AZ_BUDGETS_DB_PASSWORD="Bud$(openssl rand -hex 16)7"
docker run --rm --platform linux/amd64 -e SQLCMDPASSWORD="$SQL_ADMIN_PASSWORD" mcr.microsoft.com/mssql/server:2022-latest /opt/mssql-tools18/bin/sqlcmd -S tcp:$SQL_SERVER.database.windows.net,1433 -d $PREFIX-subscriptions-db -U $SQL_ADMIN -b -l 60 -Q "CREATE USER subscriptions_user WITH PASSWORD = '$AZ_SUBSCRIPTIONS_DB_PASSWORD'; ALTER ROLE db_ddladmin ADD MEMBER subscriptions_user; ALTER ROLE db_datareader ADD MEMBER subscriptions_user; ALTER ROLE db_datawriter ADD MEMBER subscriptions_user;"
docker run --rm --platform linux/amd64 -e SQLCMDPASSWORD="$SQL_ADMIN_PASSWORD" mcr.microsoft.com/mssql/server:2022-latest /opt/mssql-tools18/bin/sqlcmd -S tcp:$SQL_SERVER.database.windows.net,1433 -d $PREFIX-budgets-db -U $SQL_ADMIN -b -l 60 -Q "CREATE USER budgets_user WITH PASSWORD = '$AZ_BUDGETS_DB_PASSWORD'; ALTER ROLE db_ddladmin ADD MEMBER budgets_user; ALTER ROLE db_datareader ADD MEMBER budgets_user; ALTER ROLE db_datawriter ADD MEMBER budgets_user;"
# Check: subscriptions_user can open its own database but NOT the budgets one (this must fail).
docker run --rm --platform linux/amd64 -e SQLCMDPASSWORD="$AZ_SUBSCRIPTIONS_DB_PASSWORD" mcr.microsoft.com/mssql/server:2022-latest /opt/mssql-tools18/bin/sqlcmd -S tcp:$SQL_SERVER.database.windows.net,1433 -d $PREFIX-budgets-db -U subscriptions_user -l 60 -Q "SELECT 1"
az sql server firewall-rule delete --resource-group $RG --server $SQL_SERVER --name MyLaptop
```

**5. Container Apps** (a placeholder image; the first deploy replaces it and sets the settings and secrets)

```bash
az containerapp env create --name $PREFIX-env --resource-group $RG --location $APP_LOCATION
for svc in subscriptions budgets; do az containerapp create --name $PREFIX-$svc --resource-group $RG --environment $PREFIX-env --image mcr.microsoft.com/k8se/quickstart:latest --ingress external --target-port 8000 --min-replicas 0 --max-replicas 1 --cpu 0.25 --memory 0.5Gi; done
```

CORS is not set on the Container Apps ingress: each service allows the UI's address
itself (Flask-CORS with `CORS_ORIGINS`), which CD sets.

**6. The pipeline's identity: a managed identity that trusts GitHub (OIDC)**

```bash
IDENTITY=$PREFIX-github
az identity create --name $IDENTITY --resource-group $RG --location $APP_LOCATION
PRINCIPAL_ID=$(az identity show --name $IDENTITY --resource-group $RG --query principalId -o tsv)
RG_ID=$(az group show --name $RG --query id -o tsv)
az role assignment create --assignee-object-id $PRINCIPAL_ID --assignee-principal-type ServicePrincipal --role Contributor --scope $RG_ID
# GitHub may name the repository by name or by number, so both are trusted (main branch only).
az identity federated-credential create --name github-main --identity-name $IDENTITY --resource-group $RG --issuer https://token.actions.githubusercontent.com --audiences api://AzureADTokenExchange --subject "repo:adamkhouryedy2308-eng/subscription-tracker:ref:refs/heads/main"
az identity federated-credential create --name github-main-ids --identity-name $IDENTITY --resource-group $RG --issuer https://token.actions.githubusercontent.com --audiences api://AzureADTokenExchange --subject "repo:adamkhouryedy2308-eng@229741132/subscription-tracker@1389213575:ref:refs/heads/main"
```

**7. GitHub secrets and variables** (passwords go straight from the shell variable into GitHub)

```bash
gh auth login
REPO=adamkhouryedy2308-eng/subscription-tracker
az identity show --name $IDENTITY --resource-group $RG --query clientId -o tsv | gh secret set AZURE_CLIENT_ID --repo $REPO
az account show --query tenantId -o tsv | gh secret set AZURE_TENANT_ID --repo $REPO
az account show --query id -o tsv | gh secret set AZURE_SUBSCRIPTION_ID --repo $REPO
printf %s "$AZ_SUBSCRIPTIONS_DB_PASSWORD" | gh secret set SUBSCRIPTIONS_DB_PASSWORD --repo $REPO
printf %s "$AZ_BUDGETS_DB_PASSWORD" | gh secret set BUDGETS_DB_PASSWORD --repo $REPO
openssl rand -hex 32 | gh secret set SECRET_KEY --repo $REPO
gh variable set PREFIX --body $PREFIX --repo $REPO
gh variable set RESOURCE_GROUP --body $RG --repo $REPO
gh variable set UI_STORAGE --body $UI_STORAGE --repo $REPO
gh variable set SQL_SERVER --body $SQL_SERVER --repo $REPO
```

**8. Read access for the professors**

```bash
az role assignment create --assignee amartini@faculty.ie.edu --role Reader --scope $RG_ID
az role assignment create --assignee bserra@faculty.ie.edu --role Reader --scope $RG_ID
```

Then merge a pull request into `main`: CD deploys both services and the UI. The
GHCR images are public, so Azure can pull them without a password.

**Looking inside an Azure database** (used for the migration evidence): make your
own account the server's Microsoft Entra admin, then use *Query editor* in the
portal, which asks to allow your IP for the moment (delete that firewall rule afterwards):

```bash
az sql server ad-admin create --resource-group $RG --server-name $SQL_SERVER --display-name "$(az ad signed-in-user show --query userPrincipalName -o tsv)" --object-id "$(az ad signed-in-user show --query id -o tsv)"
az containerapp logs show --name $PREFIX-budgets --resource-group $RG --type console --tail 300 --format text   # the startup log, e.g. "applied migration ..."
```

## The problem

Subscriptions are cheap one by one, but they add up and are easy to forget.
Free trials silently become paid plans and prices go up without anyone
noticing. Most people cannot say how much they spend per month on
subscriptions.

## Stakeholders (invented to guide design decisions)

- **Students** – main users; tight budgets, many small subscriptions.
- **IE Student Union** – wants to offer the tool to ~5,000 students as part of
  a financial-wellbeing campaign, so many people share one app and each
  person's data must stay private.
- **Me (developer)** – has to maintain the app and later split it into
  services and deploy it to Azure (Assignment 2).

## What SubTrack does

### Domain 1 – Subscriptions (`services/subscriptions`)

- Add, edit and cancel subscriptions: name, one of 10 fixed categories (such as
  Entertainment, AI Tools, Health & Fitness), price, billing cycle (weekly,
  monthly, quarterly, yearly), first payment date, free trial and last used date.
- The list shows the monthly and yearly total, the next payment and a countdown
  ("in 2 days") for each subscription.
- Cancelled subscriptions are kept (not deleted) and show how much cancelling
  them saves per year.
- **Price history:** every price change is saved, the list shows "▲ 19%" since
  you subscribed, and the edit page shows the history (ADR-3).
- **Bank statement import:** upload a CSV export from your bank and SubTrack
  finds the payments that repeat with a regular rhythm and a similar amount,
  then suggests them as subscriptions. The file and its payments are never
  stored; only the subscriptions you confirm are saved (ADR-5).

### Domain 2 – Budgets & Alerts (`services/budgets`)

- **Spending calculator:** what each category costs per month and per year,
  and its share of the total.
- **Budgets:** a monthly budget per category with a green, amber ("close to
  the limit") or red (over) bar. Each budget has its own warning level, 80% unless
  the user picks another one (migration 003). Only the limits are stored; spending
  is worked out live (ADR-3).
- **Alerts** with a counter in the sidebar: free trial ending (7 days), over
  budget, price went up (last 30 days), payment soon (3 days) and not used for
  30 days.

### Accounts (inside the Subscriptions service)

A supporting part, not a third feature domain: sign up, log in and log out.
Passwords are stored only as a salted hash. Logging in gives a signed token that
both services check themselves with the shared `SECRET_KEY` (ADR-6), every endpoint
except `/health`, log in and sign up needs it, and each user only sees their own
data (`user_id` in every query, ADR-3).

## Decisions and AI use

- **[ADR.md](ADR.md)** – the architecture decisions: 1–5 from Assignment 1, and
  6–10 for Assignment 2 (the split, data and migrations, serverless hosting on
  Azure, pipeline and testing, and the API gateway that was not built).
- **[AI_USAGE.md](AI_USAGE.md)** – every use of AI (Claude Code), whether it
  was accepted or changed, and an explanation in my own words, including the
  workflows, Dockerfiles and Azure commands.

## How the work is organised in Git

- `main` always holds working, tested code, and since Assignment 2 everything on
  `main` is deployed to Azure.
- Each change is built on its own branch and reaches `main` through a pull
  request, so CI checks it before CD deploys it (for example `refactor/split-services`,
  `feature/docker`, `feature/ui`, `feature/ci`, `feature/budget-warn-level`).
- Pull requests are merged with **Create a merge commit**, so every commit made
  on a branch stays in the history of `main`.
- The graded version is the commit tagged `submission`.

## Scope decisions (Assignment 1)

After the professor's feedback (2026-09-29) that the first idea was "a bit
simple", three upgrades were chosen, each tied to a real user problem: the
bank statement import (people cannot type in what they have forgotten), the
alerts engine with price history (price rises and trials go unnoticed) and
the spending calculator with budgets. Login was first left out and then added
on 2026-10-01, because the Student Union scenario means many users share one
app. It uses Werkzeug's salted password hashing (which comes with Flask) and
Flask's signed session cookie. The Flask-Login extension was rejected because
it adds a package for about ten lines of code, and "Sign in with Google"
because it needs keys set up by hand, which would break the one-command setup.

Considered and **not built**:

- A machine-learning model that suggests categories: a fixed list of
  categories plus a list of known services already keeps categories
  consistent, so the model would add a large library without solving a real
  problem.
- Charts, a 12-month forecast and a timeline of upcoming charges: the budget
  bars, totals and alerts already answer "how much do I spend and what is
  coming", so these were left for later to keep the scope finishable.
- Password reset, email checks and connecting directly to a bank: each needs
  outside services or keys, which would break the one-command setup.

## SMART goals (Assignment 1)

1. **Specific:** A user can add a subscription and see its monthly cost. ✅
2. **Measurable:** Unit tests cover at least **70%** of the core business logic
   of both domains (now 100%), and the bank import finds every recurring
   payment in the sample statement with no false matches (a test checks
   exactly six). ✅
3. **Achievable:** Use only Python, Flask and SQLite (≤ 5 direct third-party
   packages; the app uses 4) so I can explain every line. ✅
4. **Relevant:** The app shows total monthly spending, any category that is
   over budget, and active alerts. ✅
5. **Time-bound:** Both domains working, tested and documented by
   **2026-10-04**. ✅
