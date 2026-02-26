# /pipeline — Match and Execute a Pipeline Template

Match a natural-language request to a pipeline template and execute it.

## Steps

1. **Parse the request** from `$ARGUMENTS`. This is the user's natural-language description of what they want to do.

2. **Load pipeline templates** from `specs/pipelines/templates/`. Read each template's metadata (name, description, required slots).

3. **Match the request** to the best pipeline template using the NL matcher:
   - Compare the user's request against each template's description and slot types.
   - Rank matches by relevance score.
   - If no match scores above the confidence threshold, tell the user and suggest available pipelines.

4. **Show match results** to the user:
   - Display the matched template name and description.
   - Show the confidence score.
   - List the slots that will be filled and their inferred values.
   - List any slots that need user input.

5. **Ask for confirmation** before executing. Never auto-execute a pipeline.

6. **Execute the pipeline** once the user confirms:
   - Fill all slots with confirmed values.
   - Run the pipeline steps in order.
   - Report results after each step.

## Arguments

- `$ARGUMENTS` — Natural-language description of the desired pipeline action.
