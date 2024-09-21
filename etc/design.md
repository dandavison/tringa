# Scope = repo

Options:
`--repo $repoid`

- See which tests are flaky: `tringa repo show`
- See tests are slow := (slow test summary for latest run): `tringa repo show`
- Run a custom query: `tringa repo sql|repl`


# scope = PR
This is just scope = (latest run of PR)

Options:
`--pr $prid`

- summary `tringa pr show`
    For each build:
    - How many failed? (passed, skipped)
    - Which are flaky?

- Run a custom query `tringa pr sql|repl`

- Rerun it! `tringa pr rerun`

