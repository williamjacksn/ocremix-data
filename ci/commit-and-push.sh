git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"
git add --all
git commit --message="${COMMIT_MESSAGE}" && echo "pushed=true" >> $GITHUB_OUTPUT || exit 0
git push
