"""Answer blocks and FAQ for the public Said & Done Ledger page.

These are short, stand-alone summaries that AI search engines can quote whole.
They add NO new facts: every figure here must already appear in the Ledger note.
build.py checks that on every run (numbers must exist in the note, word counts in range)
and refuses to pass --check if the note's version moves past FOR_VERSION, so each
quarterly update forces a re-read of every sentence below.

"{ledger}" is filled in at build time with "the Said & Done Ledger v1.0" (current version).
"""

# The Ledger version these sentences were checked against. Bump only after re-checking
# every answer and FAQ line against the new figures.
FOR_VERSION = "v1.0"

# One block per numbered section. 40–60 words each. The first sentence names the
# figure, the entity and the source.
ANSWER_BLOCKS = {
    1: "According to {ledger}, announced continental AI commitments in Africa exceed US$70bn, "
       "while verifiable deployed AI-specific capital, including infrastructure capex, is on the "
       "order of US$1–2bn. The two largest announcements, the US$60bn Africa AI Fund and the "
       "AfDB–UNDP US$10bn initiative, show no verifiable deployment.",
    2: "According to {ledger}, citing TechCabal Insights' April 2026 analysis of Dr Chinasa T. "
       "Okolo's dataset, 207 AI companies were tracked across 17 African countries in 2025, up "
       "from 104 in 2022. 86% are still active, 73% of the 2022 cohort survived three years, and "
       "Nigeria, South Africa and Kenya hold 63% of the total.",
    3: "According to {ledger}, citing the IMF's July 2026 paper on sub-Saharan Africa, installed "
       "data-centre IT capacity is about 0.4 GW, under 1% of the global total. The African Data "
       "Centres Association counts 360 MW active, 0.6% of global. Capacity roughly triples to "
       "about 1.2 GW by 2030, but the global share stays flat.",
    4: "According to {ledger}, at least 16 African countries have published or adopted a "
       "national AI strategy, starting with Mauritius in 2018, while the DRC, Uganda, Tanzania "
       "and others are still drafting. South Africa is the notable gap: its draft policy was "
       "withdrawn in April 2026, and iAfrica reports a redraft isn't expected before end-March 2027.",
    5: "According to {ledger}, citing Partech, total continental venture capital raised was "
       "US$4.1bn in 2025, up 25%; AVCA counts US$3.9bn. Q1–Q3 2026 brought US$2.16bn, about 4% "
       "below a year earlier, per Africa: The Big Deal. Dedicated AI venture capital is small: "
       "Enza Capital's AI Africa Fund reached a US$21m first close.",
    6: "According to {ledger}, citing Africa: The Big Deal, startups with a female CEO received "
       "2.2% of African startup funding in 2025, the lowest share since tracking began in 2019, "
       "and 5.4% in Q1–Q3 2026, about 2% without one large deal. Yet 19.2% of startups have at "
       "least one female co-founder, per Disrupt Africa.",
    7: "According to {ledger}, when published figures on African AI conflict, its Unresolved "
       "Register keeps both numbers and gives a one-line reason they diverge. One example: the "
       "IMF's July 2026 paper counts about 160 data centres in sub-Saharan Africa in its prose and "
       "213 in a figure on the same page, from two different sources.",
    8: "According to {ledger}, citing the IMF's July 2026 paper, AI lifts sub-Saharan African "
       "productivity by about 0.2% under current conditions, about 0.4% of GDP cumulatively over a "
       "decade, against 2.1% and about 4% under high adoption. Lead author Martin Schindler called "
       "the current-conditions figure \"little more than a rounding error.\"",
    9: "According to {ledger}, drawing on The Foundations of African AI by Africa's Protopia, "
       "today's capital, compute and startups sit on three earlier eras: The Wire (1994–2009), "
       "The Signal (2003–2011) and The Naming (2013–2019), when institutions such as the Deep "
       "Learning Indaba and AMMI gave the field its name.",
}

# Plain-language questions people actually ask, answered only from Ledger figures.
FAQ = [
    ("How much AI investment has actually been deployed in Africa?",
     "Announced continental AI commitments exceed US$70bn. Verifiable deployed AI-specific "
     "capital, including infrastructure capex, is on the order of US$1–2bn. Most of what is "
     "deployed is corporate infrastructure spending (Cassava, Google, Microsoft South Africa, the "
     "Nigerian data centres) and philanthropic programme money (Gates, IDRC, UNDP)."),
    ("How many African AI startups are active?",
     "TechCabal Insights, analysing Dr Chinasa T. Okolo's dataset, tracked 207 AI companies "
     "across 17 countries in 2025, and 86% are still active. Nigeria (50), South Africa (49) and "
     "Kenya (31) hold 63% of them. Other counts differ by definition: StartupList finds 159, and "
     "AfriLabs reports 2,400+ under a much looser test."),
    ("Why do published figures on African AI disagree?",
     "Mostly because sources count different things. Egypt has 11 AI-first startups or 44 "
     "AI-enabled ones. Partech puts 2025 venture capital at US$4.1bn and AVCA at US$3.9bn because "
     "of deal-inclusion rules. The IMF gives about 160 and 213 data centres on the same page, "
     "from two sources. The Ledger keeps both numbers and says why they diverge."),
    ("Has the US$60bn Africa AI Fund raised any money?",
     "No legal vehicle, capital call or first close has been found. In Accra in September 2026, "
     "Smart Africa cited US$18.7bn; its own written post describes that as a blended finance "
     "architecture. Public reporting reviewed as of 2 October 2026 gives no breakdown of money "
     "committed or paid in, so the Ledger carries it as structure, not capital."),
    ("How much data-centre capacity does Africa have?",
     "The IMF puts sub-Saharan Africa's installed IT capacity at about 0.4 GW, under 1% of the "
     "global total. The African Data Centres Association counts 360 MW active and 0.6% of global. "
     "Capacity is expected to roughly triple to about 1.2 GW by 2030 with no gain in global share; "
     "the United States alone holds close to 45%."),
    ("Which African countries have a national AI strategy?",
     "At least 16 have published or adopted one, including Mauritius (2018, Africa's first), "
     "Rwanda, Senegal, Egypt, Kenya, Nigeria and Ghana. The DRC, Uganda, Tanzania and others are "
     "drafting. South Africa withdrew its draft policy in April 2026. The African Union endorsed "
     "a Continental AI Strategy in July 2024."),
    ("How much funding goes to women-led African startups?",
     "Startups with a female CEO received 2.2% of funding in 2025, the lowest share since "
     "tracking began in 2019, according to Africa: The Big Deal. In Q1–Q3 2026 the share was "
     "5.4%, or about 2% without one large deal. Meanwhile 19.2% of startups have at least one "
     "female co-founder."),
    ("How is the Said & Done Ledger sourced and updated?",
     "No figure enters the Ledger without a source, and contested figures are never silently "
     "reconciled: both numbers stay, with the reason they diverge. The Ledger is updated "
     "quarterly. Replaced figures stay on the page, struck through, and every version keeps its "
     "own address."),
]
