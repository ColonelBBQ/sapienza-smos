# Statistical Methods for Official Statistics
In this repository we can find all useful information about my project for Statistical Methods for Official Statistics. The project I chose is "Analysis of Low Birth Rates Across Italian Regions Using Socio-Economic and Demographic Indicators"

## Introduction

Italy has one of the lowest fertility rates in Europe; demographic decline has implications for the labor market, welfare systems, and long-term economic stability. In this project I want to analyze how socio-economic and demographic factors differ across regions and how they relate to birth rates.

## Literature Review

### Fertility Decline in Italy: Context and Historical Trends
Italy is widely recognized as one of the earliest and most persistent cases of very low fertility in Europe. Kertzer et al. (2008) describe how Italy entered a prolonged period of below-replacement fertility as early as the 1990s, driven by a combination of late transitions into adulthood, weak welfare support, and rigid labor market conditions. Their analysis highlights the structural mismatch between family aspirations and institutional constraints, especially regarding childcare availability and women’s labor market participation.

Caltabiano (2018) adds a regional dimension to this picture, showing that Italian fertility has long been characterized by strong North–South heterogeneity, with northern regions such as Trentino-Alto Adige maintaining relatively higher fertility levels and southern regions—Sardinia being the starkest case—showing persistently lower rates. Her findings emphasize the historical continuity of regional disparities and their connection to economic and cultural differences.

More recent work by Comolli (2025) further contextualizes these trends, describing Italy as an emblematic case of “lowest-low fertility” where demographic decline, delayed family formation, and long-term uncertainty converge. She argues that Italy’s combination of precarious employment and insufficient family policy support creates a socio-economic environment in which parenthood is increasingly postponed or forgone

## Institutional and Policy Factors: The Role of Childcare and Welfare Support
Policy support emerges as another major determinant of fertility. Scherer (2023) evaluates the role of formal childcare services in Italy and finds that regions with better childcare availability tend to have higher fertility. Her study confirms a key hypothesis in demographic economics: access to affordable, high-quality childcare reduces the opportunity cost of parenthood, especially for working women.

This aligns with Kertzer et al. (2008), who argue that Italy’s limited investment in family policies historically reinforced low fertility levels. They show that the inadequacy of parental leave provisions, childcare capacity, and flexible work arrangements—combined with cultural expectations of intensive motherhood—created structural obstacles to family formation.

## Data Collection

ISTAT (single source requirement): natality data, regional demographic indicators, socio-economic indicators

Dependent Variable: 
- Tasso di fecondità totale (TFR) https://demo.istat.it/app/?i=FE1&l=it

Independent Variables:
- Female Employment Rate (15–64) -- > https://esploradati.istat.it/databrowser/#/it/dw/categories/IT1,Z0500LAB,1.0/LAB_OFFER/LAB_OFF_EMPLOY/DCCV_TAXOCCU1/IT1,150_915_DF_DCCV_TAXOCCU1_4,1.0
- Youth Unemployment Rate (15–24) --> https://esploradati.istat.it/databrowser/#/it/dw/categories/IT1,Z0500LAB,1.0/LAB_OFFER/LAB_OFF_EMPLOY/DCCV_TAXOCCU1/IT1,150_915_DF_DCCV_TAXOCCU1_4,1.0
- Average Regional Income / Disposable Income --> https://esploradati.istat.it/databrowser/#/it/dw/categories/IT1,Z0500LAB,1.0/LAB_EMPLWAGE/DCSC_RACLI/DCSC_RACLI_DISTRPROV/IT1,533_957_DF_DCSC_RACLI_13,1.0
- Education Level of Women (Share of women 25–34 with degree) --> https://esploradati.istat.it/databrowser/#/it/dw/categories/IT1,Z0820EDU,1.0/UNIVERSITY/IT1,56_190_DF_DCIS_LAUREATI_1,1.0
- Housing Cost Index / Rent Prices --> Regioni e tipo di comune https://esploradati.istat.it/databrowser/#/it/dw/categories/IT1,HOU,1.0/HOU_HOUSING/DCCV_ABITSPESA/IT1,33_225_DF_DCCV_ABITSPESA_6,1.0
- Share of Women Aged 25–39 --> independent_variable_1 calculated https://demo.istat.it/app/?i=RIC&l=it
https://demo.istat.it/app/?i=POS&l=it
- Share of Foreign Residents --> independent_variable_2 calculated https://demo.istat.it/app/?i=RIC&l=it
- Marriage Rate / Average Age at First Marriage --> https://esploradati.istat.it/databrowser/#/it/dw/categories/IT1,POP,1.0/POP_MARUNION/DCIS_MATRIND/IT1,24_84_DF_DCIS_MATRIND_1,1.0
- Availability of Childcare Services (0–3) --> https://esploradati.istat.it/databrowser/#/it/dw/categories/IT1,Z0800SSW,1.0/SSW_SOCSE/DCIS_SERVSOCEDU1/IT1,47_850_DF_DCIS_SERVSOCEDU1_2,1.0
- Public Spending on Families / Social Policies https://esploradati.istat.it/databrowser/#/it/dw/categories/IT1,Z0800SSW,1.0/SSW_SOCSE/DCIS_SERVSOCEDU1/IT1,47_850_DF_DCIS_SERVSOCEDU1_2,1.0
- Employment Stability --> https://esploradati.istat.it/databrowser/#/it/dw/categories/IT1,Z0900ENT,1.0/ENT_STRU/DICA_ADIPWP/DICA_ADIPWP_OC/IT1,183_286_DF_DICA_ADIPWP_31,1.0

## Methodology


## Analysis

## Conclusion
