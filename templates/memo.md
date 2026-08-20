# {{ candidate.name }} — {{ call_label }}

**{{ analysis.total_score }}/100** · {{ candidate.source_batch or "unbatched" }} · [{{ candidate.website }}]({{ candidate.website }})

> {{ candidate.one_liner }}

{{ analysis.call_rationale }}

**What would change this call**
{% for c in analysis.change_my_mind %}
- {{ c | oneline }}
{% endfor %}

---

## Scores

| Dimension | Weight | Score | Why |
| --- | --- | --- | --- |
{% for d in analysis.dimension_scores %}
| `{{ d.name }}` | {{ d.weight }}% | {{ d.score }}/10 | {{ d.rationale | escape_pipe }} |
{% endfor %}

## Team
{% if candidate.founders %}
{% for f in candidate.founders %}
- {{ f | oneline }}
{% endfor %}
{% endif %}

{{ analysis.team.text }}

## Product

{{ analysis.product.text }}

## Market

{{ analysis.market.text }}

## Risks / open questions

{% for r in analysis.risks %}
- {{ r.text | oneline }}
{% endfor %}

---

## Sources

{% for e in sources %}
- `{{ e.id }}` ({{ e.source }}) — [{{ e.url }}]({{ e.url }}) — "{{ e.snippet | oneline }}"
{% endfor %}

---
<sub>Scored {{ analysis.analyzed_at }} against `{{ analysis.thesis_version }}` by `{{ analysis.model_used }}`.</sub>
