# Agricultural Data Acquisition & Alignment Strategy

## 1. Initial Crop Selection & Geographic Justification

### Focus Region: Maharashtra, India
Maharashtra represents a critical agricultural zone characterized by varied agro-ecological sub-zones:
- **Vidarbha & Marathwada**: Predominantly semi-arid, rainfed cropping on Vertisols (black cotton soil). Highly vulnerable to monsoon delays, dry spells, and terminal heat stress.
- **Western Maharashtra**: Canal/well irrigated sugarcane, pulses, and vegetables.
- **Konkan**: High rainfall coastal belt primarily cultivated with rice.

### Crop Comparison: Soybean vs. Rice

| Evaluation Metric | Soybean (*Glycine max*) | Rice (*Oryza sativa*) | Recommendation & Decision |
|---|---|---|---|
| **State Production Share** | Maharashtra is #2 in India (~30-40% national output). | ~3-4% national output, concentrated in Konkan. | **Soybean**: High national and state relevance. |
| **Acreage Distribution** | >4.2 million hectares across 20+ central & eastern districts. | Confined mostly to 5-6 coastal districts. | **Soybean**: Broader geographic variation for ML. |
| **Monsoon/Climate Sensitivity** | Predominantly rainfed; strong yield response to Kharif rainfall fluctuations. | Often supplemented by heavy rainfall or coastal irrigation. | **Soybean**: High variance explained by weather & soil. |
| **Historical Data Consistency** | Reliable district-level records since 1997-98 across DES & APY portals. | Long historical records, but localized to coastal belt. | **Soybean**: Highly consistent for Maharashtra's agro-climate. |

**Decision**: **Soybean** during the **Kharif** season (sown June/July, harvested September/October) is chosen as the primary initial crop. The pipeline is designed with multi-crop extensibility so Rice and Cotton can be activated using the exact same schema.

---

## 2. Target Data Sources & Licensing

### 1. Historical Agricultural Production & Area
- **Source**: Directorate of Economics & Statistics (DES), Ministry of Agriculture & Farmers Welfare, Government of India.
- **Portal**: [AgriStats / APS](https://aps.dac.gov.in) & [Open Government Data (OGD) Platform India (data.gov.in)](https://data.gov.in).
- **Secondary Reference**: ICRISAT District Level Database (DLD) for Indian Agriculture (1966-2017 harmonized 1966 district boundaries).
- **Fields Collected**: State, District, Crop, Year, Season, Area (Hectares), Production (Metric Tonnes).
- **Derived Target Metric**:
  $$\text{Yield (tonnes/ha)} = \frac{\text{Production (Metric Tonnes)}}{\text{Area (Hectares)}}$$
- **Data Filtering & Integrity Rules**:
  - Filter out records where $\text{Area} < 100 \text{ ha}$ (to avoid erratic outlier ratios from tiny experimental plots).
  - Screen for unrealistic yields outside the biological envelope for rainfed soybean ($0.1 \le \text{Yield} \le 5.0 \text{ t/ha}$).
  - Normalize district boundary changes (e.g., Bifurcation of Akola/Washim, Parbhani/Hingoli).

### 2. Historical Weather & Agroclimatology
- **Source**: NASA POWER (Prediction Of Worldwide Energy Resources) Agroclimatology Project.
- **Spatial Resolution**: $0.5^\circ \times 0.5^\circ$ latitude/longitude grid (~50 km).
- **Access**: Free public REST API / bulk geospatial extraction.
- **Temporal Coverage**: Daily data from 1990 to present.
- **Key Parameters**:
  - `PRECTOTCORR`: Corrected total precipitation ($\text{mm/day}$).
  - `T2M_MAX`: Maximum temperature at 2 meters ($^\circ\text{C}$).
  - `T2M_MIN`: Minimum temperature at 2 meters ($^\circ\text{C}$).
  - `ALLSKY_SFC_SW_DWN`: All-sky insolation incident on a horizontal surface ($\text{MJ/m}^2/\text{day}$).
  - `RH2M`: Relative humidity at 2 meters ($\%$).
- **Seasonal Aggregations (Kharif: Day of Year 152 to 304 / June 1 to October 31)**:
  - Cumulative seasonal rainfall ($\text{mm}$).
  - Mean growing season maximum temperature ($^\circ\text{C}$).
  - Mean growing season minimum temperature ($^\circ\text{C}$).
  - Mean solar radiation ($\text{MJ/m}^2/\text{day}$).
  - Mean relative humidity ($\%$).
  - Count of consecutive dry days ($<2.5\text{ mm}$ rainfall during reproductive phase in August-September).

### 3. Soil Properties
- **Source**: ISRIC SoilGrids 2.0 (Global Gridded Soil Information).
- **Spatial Resolution**: 250m gridded resolution.
- **Access**: Open Database License (ODbL) via Web Coverage Service (WCS) / GeoTIFF downloads.
- **Depth Interval**: Weighted average for topsoil ($0\text{--}30\text{ cm}$).
- **Target Properties**:
  - `phh2o`: Soil pH in $\text{H}_2\text{O}$ ($\times 10$).
  - `soc`: Soil organic carbon content ($\text{dg/kg} \rightarrow \%$).
  - `clay`: Clay content ($<2\,\mu\text{m}$) fraction ($\text{g/kg} \rightarrow \%$).
  - `sand`: Sand content ($50\text{--}2000\,\mu\text{m}$) fraction ($\text{g/kg} \rightarrow \%$).
  - `bdod`: Bulk density of fine earth ($\text{cg/cm}^3 \rightarrow \text{g/cm}^3$).
  - `cec`: Cation exchange capacity at $\text{pH } 7$ ($\text{mmol(c)/kg} \rightarrow \text{cmol(+)/kg}$).
- **Aggregation**: Area-weighted median across agricultural cropland pixels within each district boundary polygon.

---

## 3. Dataset Alignment Strategy

```
  Crop Statistics (DES)          NASA POWER Weather              ISRIC SoilGrids
  [District, Year, Crop, Yield]  [District Centroid, Daily]      [District Boundary, 250m]
              │                              │                               │
              │                              ▼ Kharif Aggregation            ▼ Zonal Median
              │                     [District, Year, Weather]       [District, Soil]
              │                              │                               │
              └──────────────────────────────┼───────────────────────────────┘
                                             ▼
                                  Aligned Modeling Dataset
                        [District, Year, Crop, Weather, Soil, Yield]
```

### Alignment Keys:
- Primary key: `(state, district, crop, season, year)`.
- Temporal alignment: Weather aggregated specifically across the corresponding crop year's Kharif vegetative and reproductive window.
- Spatial alignment: Standardized district names mapped via alias dictionary to resolve historical spelling variations (e.g. "Osmanabad" vs "Dharashiv", "Aurangabad" vs "Chhatrapati Sambhajinagar").

---

## 4. Known Data Limitations & Ethical Governance

1. **Spatial Aggregation Smearing**: District-level statistics average out intra-district microclimates and field-level soil variance. The model provides macro-level decision support, not parcel-level precision.
2. **Management Factor Omission**: Official public records do not capture precise fertilizer application rates, sowing dates, irrigation events, or pesticide applications per farmer. Features represent environmental potential and risk rather than farm management actions.
3. **No Causal Inferences**: Model feature importances (e.g., high clay content association with yield) represent statistical correlations, not direct causal claims.
