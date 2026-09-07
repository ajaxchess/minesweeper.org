https://claude.com/blog/the-ai-native-sdlc-playbook
I want to refactor the minesweeper.org repo according to the workflow outlined by the Claude Blog post "The AI-Native SDLC Playbook".

Please discuss what we would want to do to make the current workflow look more like what is outlined in that post.

I would also like to begin incorporating annotated tags into the minesweeper.org release workflow.
Ideally, after the staging environment runs against a new commit, if the tests pass, we should add a tag saying that that commit has
passed our staging test suite.  Let's call that tag staging-tested and the annotation will preserve the date of the test.
Make sure that the staging workflow pushes that tag.
