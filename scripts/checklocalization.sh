for f in ../templates/*.html; do
  count=$(grep -o '{{ *t[\.\[]' "$f" | wc -l)
  echo "$count  $f"
done | sort -n
#Templates with 0–3 {{ t. }} references but listed in sitemap.xml are the priority targets.
#Decide which pages deserve translation (the high-priority ones already in the sitemap) and which should stay English-only (the niche tool pages). For the high-priority set: extract every English string into t.* keys and add translations for the supported languages. For the rest: leave English-only and apply the page_localized = false guard from A1.

