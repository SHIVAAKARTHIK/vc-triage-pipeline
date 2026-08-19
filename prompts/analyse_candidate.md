## Candidate: {{ candidate.name }}

One-liner: {{ candidate.one_liner }}
Website: {{ candidate.website }}
YC batch: {{ candidate.source_batch or "unknown" }}
Traction: {{ candidate.traction.kind }} -- {{ candidate.traction.detail }}

Founders:
{% if candidate.founders %}
{% for f in candidate.founders %}
- {{ f }}
{% endfor %}
{% else %}
(none found)
{% endif %}

## Evidence

{% for e in candidate.evidence %}
- id: `{{ e.id }}`
  source: {{ e.source }}
  url: {{ e.url }}
  snippet: "{{ e.snippet }}"
{% endfor %}

Analyse this candidate against the thesis above. Cite only the evidence ids listed here.
