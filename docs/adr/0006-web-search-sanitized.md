# Web search is sanitized to prevent data egress

The web search tool is kept but wrapped so its queries can contain only generic terms — never asset names, readings, or identifying data. Even with a self-hosted Azure-resident model, search queries leave Azure to a third-party search provider, which would violate the customer's data-governance expectation. The wrapper is deliberate: do not remove it for "better search results."
