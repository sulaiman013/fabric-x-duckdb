# Phase 4: the Fabric App

Research and build plan for the application layer, written after probing the
tenant rather than reading the docs and hoping. Every availability claim below
was tested against the live workspace on 2026-09-18.

## 1. What a Fabric App actually is

Fabric Apps (preview since May 2026, Rayfin SDK since June 2026) let you define
an application backend in TypeScript and deploy it as a first-class Fabric item.
You write data models as decorated classes; the platform generates the API,
identity, access policies and hosting. The tooling is the **Rayfin** SDK and CLI.

Two templates matter here:

| Template | What it gives you | Fits which surfaces |
| --- | --- | --- |
| `dataapp` | Fabric auth, semantic model connectivity, DAX generation, analytical visual components | the six **analytics** pages |
| default / custom | Rayfin entities, generated CRUD API, own backing store | the four **operational** queues |

The `dataapp` template reads an existing semantic model through the
[Execute DAX Queries REST API](https://learn.microsoft.com/rest/api/power-bi/datasets/execute-dax-queries).
That detail decides the architecture, and section 4 explains why.

## 2. The blocker, established by probe rather than by reading

The workspace sits on `capacityRegion: "UK South"`, on the trial FTL64 capacity.
Both capacities on the tenant are UK South.

Creating the item type directly:

```
POST /workspaces/{ws}/items   {"type": "AppBackend"}
  -> 403 FeatureNotAvailable   "The feature is not available"

POST /workspaces/{ws}/items   {"type": "App" | "FabricApp" | "DataApp"}
  -> 400 InvalidItemType
```

The contrast is the whole diagnostic. Three invented names are rejected as
*invalid types*; `AppBackend` is recognised as a real type and then refused as
an *unavailable feature*. So this is not a typo and not a tenant setting. Both
relevant tenant settings are already on:

| Tenant setting | State |
| --- | --- |
| `AppBackendTenant` (Enable Fabric App Items, preview) | **enabled** |
| `DatasetExecuteQueries` (Semantic Model Execute Queries REST API) | **enabled** |

It is the region gate. The published region table lists UK South as
"Not available: Fabric App (preview)", and the probe agrees.

### Why we cannot simply re-region the existing trial

A Fabric trial capacity **does** let you choose its region: the activation
prompt offers a region dropdown and the tenant home region is only the default.
So region is a choice, not a fate.

The problem is timing. Our trial already exists, it is UK South, and it is the
capacity holding the mirrored database, the lakehouse, the 49.4M-row gold layer
and the semantic model. Moving a workspace with Fabric items to a capacity in a
different region requires **deleting every Fabric item first**. Cancelling the
trial to restart it elsewhere destroys Phases 1 to 3.

So the existing trial stays exactly where it is. The app needs a *second*
capacity, and section 5 is about how to get one.

### The region list moves, so re-probe rather than trust notes

A previous Fabric App attempt on this machine was blocked in **East US**. East US
is now supported. Notes recording a region as blocked go stale within months.
The `AppBackend` probe above takes five seconds and is authoritative; run it
before believing any table, including this one.

Supported at time of writing: Central US, East US, North Central US, West US,
West US 2, West Europe, France Central, Italy North, Norway East, Sweden Central,
Switzerland North, UAE North, South Africa North, East Asia, Southeast Asia,
Australia East, Central India, Japan East, Korea Central.

Not supported: UK South (ours), Malaysia West, and others.

## 3. What *is* available in UK South, also by probe

| Item type | Result |
| --- | --- |
| `UserDataFunction` | **201 Created** |
| `SQLDatabase` | **202 Accepted** |

Both probe items were deleted after the test. This matters because the
write-back design in `APP_DESIGN.md` section 9 depends on exactly these two
item types, and they work here today. The operational half of the app is not
blocked at all. Only the Fabric App shell is.

## 4. The architectural consequence, which is good news

The `dataapp` template reaches the semantic model over the **Execute DAX Queries
REST API**. That is an authenticated network call, not a OneLake-local read.

So the app does not have to live in the same region as the data.

An `AppBackend` item in any supported region can query `fincrime_model` in UK
South. The 49.4M-row gold layer, the Direct Lake model and the mirror all stay
exactly where they are. Only the thin application shell moves. Nothing is
re-uploaded, nothing is re-modelled, and the 29-minute seed is never repeated.

## 5. Options

### Option A: second trial, second user, supported region (recommended, free)

We are signed in as `sulaiman@sulaimanfabrictrialgmail.onmicrosoft.com`. That is
a self-created trial tenant, which means we control its directory and can add
users to it.

A Fabric trial is one per *user*, not one per tenant, and the region is chosen
at activation. So:

1. Create a second user in the tenant.
2. Sign in as that user and start a Fabric trial, selecting a **supported**
   region from the activation dropdown. West Europe is closest to the UK South
   data; UAE North and Southeast Asia are also supported and happen to sit in
   the target job markets, which is worth something in a portfolio conversation.
3. Create a workspace on that new trial capacity.
4. Grant that user Read and Build on `fincrime_model`. Same tenant, so this is
   an ordinary permission grant.
5. Deploy the Fabric App there, pointed at the model by share link.

* **Free**, and non-destructive: the UK South trial and everything on it is
  untouched.
* Delivers the genuine article: a real `AppBackend` item, deployed and running.
* 60-day clock on the second trial, same as the first.

### Option B: F2 capacity in a supported region (paid fallback)

If the second-user route is blocked for any reason, create an F2 in West Europe
and put the app workspace on that.

* F2 pay-as-you-go runs roughly USD 0.36/hour and **capacities can be paused**.
  Resumed only while building and recording, a realistic total is a few dollars,
  not a monthly SKU.
* Requires an Azure subscription with a payment method.

### Option C: translytical task flow app, entirely in UK South

Power BI report over the existing Direct Lake model, with write-back through
User Data Functions into a Fabric SQL database. Both item types are confirmed
available here. This is already specified in `APP_DESIGN.md` section 9.

* Zero extra cost, works today, no region dependency.
* Not a "Fabric App" item. It is the older translytical pattern.
* Weaker as a portfolio differentiator, because the operational surfaces are
  constrained to what a Power BI report can express. A genuine triage queue with
  assignment and a detail panel is a stretch in a report.

### Option D: build the source now, deploy when the region opens

Scaffold and develop against `npm run dev`, commit the app source, and run
`npx rayfin up` whenever UK South is enabled.

* Free, and the work is not wasted.
* Cannot be demonstrated running, which is most of the point of a portfolio piece.

### Recommendation

**A, with B as the paid fallback. C is not a competitor, it is the other half.**

The operational write-back belongs in User Data Functions plus a Fabric SQL
database whichever way this goes, because a mirrored database is read-only and
state has to live somewhere. That work is unblocked in UK South today and is
worth doing first regardless.

Option A then adds the proper application shell over the top, for free. If the
second-trial route turns out to be blocked, B buys the same outcome for a few
dollars, and if neither is wanted, the same User Data Functions are driven from
a Power BI report instead and none of the work is wasted.

That ordering is deliberate: every step before the region decision is useful in
all four options, so the decision can be deferred without stalling.

## 6. Build plan

Prerequisites already satisfied: Node v24.15.0, npm 11.12.1, both tenant
settings enabled, semantic model `fincrime_model` live and DAX-verified.

| Step | Work | Depends on |
| --- | --- | --- |
| 1 | Fabric SQL database `fincrime_ops`, tables per `APP_DESIGN.md` section 9 | nothing, works in UK South now |
| 2 | User Data Functions: assign, disposition, escalate, bulk close | step 1 |
| 3 | Prove write-back end to end: call a UDF, read the row back | step 2 |
| 4 | Confirm the SQL database auto-mirrors to OneLake as Delta | step 1 |
| 5 | Second user, second trial in a supported region, new workspace on it | region decision |
| 6 | `npm create @microsoft/rayfin@latest -- fincrime-console --template dataapp --workspace <ws>` | step 5 |
| 7 | Point the app at `fincrime_model` by share link, build the six analytics pages | step 6 |
| 8 | Wire the four operational queues to the UDFs from step 2 | steps 2, 7 |
| 9 | `npx rayfin up`, verify the deployed item | step 8 |

Steps 1 to 4 are unblocked and can start immediately. Step 5 is the only one
that needs a decision.

### The closed loop, which is the part worth showing

Step 4 is not housekeeping. A Fabric SQL database mirrors itself to OneLake as
Delta parquet automatically, with no configuration. So an analyst disposition,
written through a User Data Function into `fincrime_ops`, lands in OneLake as
data, where the next gold rebuild can join it back to `fact_alert`.

That closes the loop the pipeline currently leaves open: the model tells you
which alerts to work, the app records what the analyst decided, and that
decision becomes an input to the next model. Alert precision stops being
simulated and starts being measured against real dispositions.

Most portfolio pipelines stop at the dashboard. This one writes back.

## 7. Open questions

1. Which region for the second trial? West Europe is closest to the data. UAE
   North and Southeast Asia are equally supported and sit in the target job
   markets.
2. Mirror the operational tables back into the gold layer on the next rebuild,
   or leave the loop documented but not wired?

Neither blocks steps 1 to 4.
