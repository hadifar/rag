# Add a component

## Description

Add a presentational React component. Use for new UI inside a feature.

## Steps

1. Check `frontend/src/shared/ui/` for a primitive.
2. Create the component in `frontend/src/features/<name>/components/`.
3. Take data and actions from a hook or context of the same feature.
4. If the component has behavior, add a test in `frontend/tests/unit/components/`.
5. Validate the change. See [Run validation](../run-validation.md).

## Rules

* A component presents data only. Put parsing and calculation in `model/` or `hooks/`.
* Do not import `api/` or `@tanstack/react-query` in a component.
* Use a primitive's `className` for layout only: margin, alignment, width, `flex-1`.
* If a primitive needs a new look, add a variant to the primitive.
* Use role colors (`primary`, `danger`, `success`, `warning`) and `slate`. Other palettes fail `tests/unit/architecture/colors.test.ts`.
* Add `box-border` to a full-width element with padding. Tailwind preflight is not loaded.
* Show errors with `errorMessage` or `errorDetail` from `frontend/src/shared/api/errors.ts`.
