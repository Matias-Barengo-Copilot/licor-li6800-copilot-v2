/**
 * Data loader: ports data_loader.py.
 * Attendance from DB; work and yearly use static fallback data.
 */
import type { WorkRow } from "./analytics";

// ─── Work ─────────────────────────────────────────────────────────────────────

export function loadWork(): WorkRow[] {
  // Work tracking not yet in DB — empty array with expected schema
  return [];
}

// ─── Yearly enrollment ────────────────────────────────────────────────────────

export interface EnrollRow {
  Program: string;
  "2022_23": number | null;
  "2023_24": number | null;
  "2024_25": number | null;
}

export function loadYearly(): EnrollRow[] {
  return [
    { Program: "Summer Core",                    "2022_23": 88, "2023_24": 96,  "2024_25": 96 },
    { Program: "After-school Core",              "2022_23": 88, "2023_24": 103, "2024_25": 99 },
    { Program: "Advanced",                       "2022_23": 44, "2023_24": 58,  "2024_25": 90 },
    { Program: "Studio",                         "2022_23": 14, "2023_24": 20,  "2024_25": 29 },
    { Program: "Play Lab",                       "2022_23": null, "2023_24": null, "2024_25": 8 },
    { Program: "Senior XP (Summer)",             "2022_23": null, "2023_24": null, "2024_25": 22 },
    { Program: "Spring Break Game Design Lab ",  "2022_23": null, "2023_24": 46,  "2024_25": 51 },
  ];
}

// ─── Demographics ─────────────────────────────────────────────────────────────

export function loadDemographicsSummary() {
  const ENROLL_2324 = 277;
  const ENROLL_2425 = 344;

  function project(pctStr: string, newTotal: number): [number, number] {
    const pct = parseFloat(pctStr.replace("%", "")) / 100;
    return [Math.round(pct * 100 * 10) / 10, Math.round(pct * newTotal)];
  }

  const raceSrc: Array<[string, string, number]> = [
    ["Black or African-American",         "25%", 55],
    ["Hispanic or Latinx",                "36%", 78],
    ["Asian",                             "29%", 63],
    ["White",                              "9%", 20],
    ["American Indian / Alaska Native",    "1%",  3],
    ["Middle Eastern / North African",     "0%",  0],
    ["Native Hawaiian / Pacific Islander", "0%",  0],
    ["Prefer not to say",                  "5%", 13],
  ];
  const race = raceSrc.map(([label, pctStr, n2324]) => {
    const [pctF, n2425] = project(pctStr, ENROLL_2425);
    return {
      category: label,
      pct_2324: parseFloat(pctStr),
      n_2324: n2324,
      pct_2425: pctF,
      n_2425: n2425,
    };
  });

  const genderSrc: Array<[string, string, number]> = [
    ["Man or Boy",                        "62%", 155],
    ["Woman or Girl",                     "34%",  84],
    ["Non-Binary / Gender Non-Conforming", "4%",  11],
    ["Another identity",                   "0%",   0],
    ["Prefer not to say",                  "3%",   7],
  ];
  const gender = genderSrc.map(([label, pctStr, n2324]) => {
    const [pctF, n2425] = project(pctStr, ENROLL_2425);
    return {
      category: label,
      pct_2324: parseFloat(pctStr),
      n_2324: n2324,
      pct_2425: pctF,
      n_2425: n2425,
    };
  });

  return {
    race,
    gender,
    disability: [
      { category: "Has Disability", pct_2324: 7,  n_2324: 10,  pct_2425: 7,  n_2425: 24 },
      { category: "No / Unknown",   pct_2324: 93, n_2324: 132, pct_2425: 93, n_2425: 320 },
    ],
    grade: [
      { category: "9th Grade",  pct_2324: 35, n_2324: 97,  pct_2425: 35, n_2425: 120 },
      { category: "10th Grade", pct_2324: 30, n_2324: 83,  pct_2425: 30, n_2425: 103 },
      { category: "11th Grade", pct_2324: 22, n_2324: 61,  pct_2425: 22, n_2425: 76  },
      { category: "12th Grade", pct_2324: 13, n_2324: 36,  pct_2425: 13, n_2425: 45  },
    ],
    income: [
      { category: "< $50,000",           pct_2324: 42, n_2324: 116, pct_2425: 42, n_2425: 145 },
      { category: "$50,000 – $74,999",   pct_2324: 25, n_2324: 69,  pct_2425: 25, n_2425: 86  },
      { category: "$75,000 – $99,999",   pct_2324: 15, n_2324: 42,  pct_2425: 15, n_2425: 52  },
      { category: "$100,000 – $200,000", pct_2324: 12, n_2324: 33,  pct_2425: 12, n_2425: 41  },
      { category: "> $200,000",          pct_2324: 6,  n_2324: 17,  pct_2425: 6,  n_2425: 20  },
    ],
    attendance_rates: [
      { program: "Spring Break Lab",  rate_2324: 83,   rate_2425: 85  },
      { program: "Senior XP",         rate_2324: null, rate_2425: 88  },
      { program: "Summer Core",       rate_2324: 94,   rate_2425: 93  },
      { program: "After-school Core", rate_2324: 84,   rate_2425: 82  },
      { program: "Advanced",          rate_2324: 85,   rate_2425: 87  },
      { program: "Studio",            rate_2324: 87,   rate_2425: 89  },
      { program: "Play Lab",          rate_2324: null, rate_2425: 85  },
    ],
    location: [
      { category: "Brooklyn",      pct_2324: 38, n_2425: 131 },
      { category: "Bronx",         pct_2324: 24, n_2425: 83  },
      { category: "Queens",        pct_2324: 20, n_2425: 69  },
      { category: "Manhattan",     pct_2324: 14, n_2425: 48  },
      { category: "Staten Island", pct_2324: 3,  n_2425: 10  },
      { category: "Non-NYC",       pct_2324: 1,  n_2425: 3   },
    ],
    enrollment_2324: ENROLL_2324,
    enrollment_2425: ENROLL_2425,
    note: "2024/25 demographic counts projected proportionally from SY2023-24 actuals.",
  };
}
