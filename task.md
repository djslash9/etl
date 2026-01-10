# Task: Update Client Onboarding App

## Schema & Data
- [ ] Define new columns for `Brands` and `Competitors` tabs:
    - [ ] `linkedin_access` (JSON)
    - [ ] `tiktok_access` (JSON)
- [ ] Update `init_db` to automatically add these headers if missing.
- [ ] Update `save_brand` and `save_competitor` to handle these new fields.
- [ ] Update `get_org_details` to return these new fields.
- [ ] Update `render_export` to include `LinkedIn Access` and `TikTok Access`.

## User Interface
- [ ] Update `render_entity_form` (helper for UI inputs) to include:
    - [ ] LinkedIn Access (Yes/No + Details)
    - [ ] TikTok Access (Yes/No + Details)
- [ ] Remove `st.balloons()` from success actions.
- [ ] Ensure Success/Error messages are displayed clearly.
- [ ] Verify form behavior (ensure inputs are validated correctly on submit).

## Verification
- [ ] Test adding a new client with the new fields.
- [ ] Test editing the new fields.
- [ ] Test export correctness.
