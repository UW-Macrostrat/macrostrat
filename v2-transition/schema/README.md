# Schema profiles

## Idea: profiles for testing/dev/prod

- Organized as folders
- Schema files can be added to each as appropriate
- Profiles nest (e.g. `dev` inherits from `staging` inherits from `prod`)
- Different sql run for each profile