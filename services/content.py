"""
Content registry for the LI-6800 Portable Photosynthesis System post-purchase experience.
"""

VIDEOS: list[dict] = [
    {
        "title": "Unpacking the LI-6800",
        "description": "Walk through the instrument components and get everything out of the box correctly.",
        "wistia_id": "5dsvm282p1",
        "url": "https://fast.wistia.net/embed/iframe/5dsvm282p1",
        "thumbnail": "",
        "local_file": "",
        "duration": "Getting Started",
        "source_url": "https://www.licor.com/support/LI-6800/videos/unpacking-the-li-6800.html",
    },
    {
        "title": "LI-6800 Software Overview",
        "description": "A tour of the LI-6800 interface with software developer Waheeda Sulaman.",
        "wistia_id": "5x8p6i4thr",
        "url": "https://fast.wistia.net/embed/iframe/5x8p6i4thr",
        "thumbnail": "",
        "local_file": "",
        "duration": "Getting Started",
        "source_url": "https://www.licor.com/support/LI-6800/videos/software-intro.html",
    },
    {
        "title": "How to Take a Basic Survey Measurement",
        "description": "Step-by-step guide to taking your first photosynthesis measurement in the field.",
        "wistia_id": "w1k3fe3d3y",
        "url": "https://fast.wistia.net/embed/iframe/w1k3fe3d3y",
        "thumbnail": "",
        "local_file": "",
        "duration": "Measurements",
        "source_url": "https://www.licor.com/support/LI-6800/videos/survey-measurement.html",
    },
    {
        "title": "Using the Dynamic Assimilation™ Technique",
        "description": "Take faster CO2 response curves during non-steady-state conditions.",
        "wistia_id": "ynukb09jy4",
        "url": "https://fast.wistia.net/embed/iframe/ynukb09jy4",
        "thumbnail": "",
        "local_file": "",
        "duration": "Measurements",
        "source_url": "https://www.licor.com/support/LI-6800/videos/dynamic-assimilation-technique.html",
    },
    {
        "title": "Warmup Tests",
        "description": "How to run system tests after startup to verify everything is working correctly.",
        "wistia_id": "ojislu9tr3",
        "url": "https://fast.wistia.net/embed/iframe/ojislu9tr3",
        "thumbnail": "",
        "local_file": "",
        "duration": "Getting Started",
        "source_url": "https://www.licor.com/support/LI-6800/videos/system-tests.html",
    },
    {
        "title": "Maintenance Overview",
        "description": "Routine maintenance tasks to keep your LI-6800 performing at its best.",
        "wistia_id": "x7hk81shpi",
        "url": "https://fast.wistia.net/embed/iframe/x7hk81shpi",
        "thumbnail": "",
        "local_file": "",
        "duration": "Maintenance",
        "source_url": "https://www.licor.com/support/LI-6800/videos/maintenance-overview.html",
    },
]

PAPERS: list[dict] = [
    {
        "title": "Simultaneous leaf-level measurement of trace gas emissions and photosynthesis with a portable photosynthesis system",
        "authors": "Riches M.J., Lee D., Farmer D.K.",
        "journal": "Atmospheric Measurement Techniques",
        "year": 2020,
        "doi": "10.5194/amt-13-4123-2020",
        "url": "https://doi.org/10.5194/amt-13-4123-2020",
    },
    {
        "title": "Gas exchange measurements in the unsteady state",
        "authors": "Saathoff A.J., Welles J.",
        "journal": "Plant, Cell & Environment",
        "year": 2021,
        "doi": "10.1111/pce.14178",
        "url": "https://doi.org/10.1111/pce.14178",
    },
    {
        "title": "Simultaneously measuring carbon uptake capacity and chlorophyll a fluorescence dynamics in algae",
        "authors": "Hupp J., McCoy J., Millgan A., Peers G.",
        "journal": "Algal Research",
        "year": 2021,
        "doi": "10.1016/j.algal.2021.102399",
        "url": "https://doi.org/10.1016/j.algal.2021.102399",
    },
    {
        "title": "Open-source LED lamp for the LI-6800 photosynthesis system",
        "authors": "Stinziano J.R. et al.",
        "journal": "bioRxiv (preprint)",
        "year": 2023,
        "doi": "10.1101/2023.10.18.562806",
        "url": "https://doi.org/10.1101/2023.10.18.562806",
    },
]

MANUAL: dict = {
    "title": "Using the LI-6800 Portable Photosynthesis System v2.1",
    "version": "2.1",
    "url": "https://licor.app.boxenterprise.net/s/7auwlt1elh71rjxtmxxpbb27ddetgm9j",
    "file_size": "~25 MB",
    "pages": "~500",
}

QUICK_START: dict = {
    "title": "LI-6800 Quick Start Guide",
    "url": "https://licor.app.boxenterprise.net/s/6byjelalcwvfr37ppwoz2lvrjup3lhev",
    "file_size": "~2 MB",
}


def get_content() -> dict:
    return {
        "videos": VIDEOS,
        "papers": PAPERS,
        "manual": MANUAL,
        "quick_start": QUICK_START,
    }
