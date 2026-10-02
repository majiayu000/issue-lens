# Turn a GitHub issue into a test charter

This worked example uses a real row from the committed [CLI report](../out/report_cli.md).
It teaches manual test design. It does not claim that your product has the same bug.
For automated drafts, see [Codex CLI planning](../README.md#generate-a-test-plan-with-codex-cli).

## 1. Read the original issue

[cli/cli #2661](https://github.com/cli/cli/issues/2661) asks for clearer guidance when
GitHub organization SAML enforcement prevents an operation. The report describes
an authenticated user encountering an organization-access error while creating a PR.
The original issue discusses re-authentication; its labels include `enhancement`.
That makes it a useful onboarding/error-message case, not evidence of a crash.

Keep the distinction between an observed upstream symptom and a hypothesis for
your product. Read the source before copying a root cause or remedy.

## 2. Map it to a capability you actually have

If your CLI connects to organizations or workspaces, ask whether account login and
workspace authorization are separate. If it has no such capability, skip this case.
Do not add SAML support just because an upstream issue mentions it.

The following charter is a proposed test for a product with that capability:

> Explore an organization-scoped operation with a logged-in test account that
> lacks organization access, to discover whether the error explains the missing
> authorization and the next step without claiming that the operation succeeded.

## 3. Record evidence from your own run

Use a test account and a non-production workspace. Record the product version,
operation, expected authorization state, exit status and visible error. Check
whether the operation leaves an unintended partial result. Then grant the needed
access and repeat the same operation to check recovery. Do not record tokens or
private organization data.

These are suggested test questions, not results. Your permission model determines
which cases and expected outcomes apply.

## 4. Find adjacent cases

After [rebuilding the corpus](../README.md#quick-start), run from the repository root:

```bash
python3 s04_search.py --form cli --q "SAML" --sort relevance
python3 s04_search.py --form cli --q "authentication" --sort relevance
```

Results depend on your current corpus. FTS keywords retrieve candidates; they do
not establish an identical root cause. Reaction counts prioritize reading, not
bug severity or prevalence in your product. The corpus can include implemented
feature requests, so classify the source manually before designing a test.

For the exploratory-testing approach, see this [author's charter guidance](https://github.com/Maaikees/exploratory-testing/blob/master/exploratory-testing-with-the-team.md).
For corpus selection and limits, read [research](research.md) and the
[known limitations](../README.md#known-limitations). Automatic extraction and planning
produce suggestions that still need this source and applicability review.
