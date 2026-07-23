EnvironmentalResearch212(2022)113577
Contents lists available at ScienceDirect
Environmental Research
journal homepage: www.elsevier.com/locate/envres
Minimization of measuring points for the electric field exposure map
generation in indoor environments by means of Kriging interpolation and
selective sampling
A. Martínez-Gonza ´ lez*, J. Monzo ´ -Cabrera, A.J. Martínez-Sa ´ ez, A.J. Lozano-Guerrero
Electromagnetics and Matter Group, Universidad Polit´ecnica de Cartagena, Campus Muralla, Cartagena, E-30202, Spain
A R T I C L E I N F O A B S T R A C T
Keywords: In a world with increasing systems accessing to radio spectrum, the concern for exposure to electromagnetic
Electromagnetic field radiation map fields is growing and therefore it is necessary to check limits in those areas where electromagnetic sources are
Kriging interpolation working. Therefore, radio and exposure maps are continuously being generated, mainly in outdoor areas, by
Spatial data analysis
using many interpolation techniques. In this work, Surfer software and Kriging interpolation have been used for
Non ionizing radiation
the first time to generate an indoor exposure map. A regular measuring mesh has been generated. Elimination of
Measuring point reduction
Less Significant Points (ELSP) and Geometrical Elimination of Neighbors (GEN) strategies to reduce the
measuring points have been presented and evaluated. Both strategies have been compared to the map generated
with all the measurements by calculating the root mean square and mean absolute errors. Results indicate that
ELSP method can reduce up to 70% of the mesh measuring points while producing similar exposure maps to the
one generated with all the measuring points. GEN, however, produces distorted maps and much higher error
indicators even for 50% of eliminated measuring points. As a conclusion, a procedure for reducing the measuring
points to generate radio and exposure maps is proposed based on the ELSP method and the Kriging interpolation.
1. Introduction Non-Ionizing Radiation Protection (ICNIRP, 2020), the Institute of
Electrical and Electronics Engineers (IEEE, 2019), the Federal Commu-
The electromagnetic (EM) environment in cities has experienced an nications Commission (Cleveland and Ulcek, 1999), or the European
explosive growth since the 1990s due to mobile communications and the Union (EU) (Recommendation C. 1999; Directive, 2013/35/EU).
usage of wireless technologies for internet access (Santana et al., 2017). The exposure levels can be measured with specific instruments such
Thus, the signal of these cellular systems is overlapping with other radio as electric or magnetic field probes that consider all the electromagnetic
signals from TV, FM, AM, Bluetooth, satellite communications, radar, sources in a frequency range (ICNIRP 1998; Pinheiro et al., 2015, ITU
navigation systems, etcetera. 2014) although other instruments such as spectrum analyzers may be
Additionally, nowadays, it is very common to find radiofrequency used when specific frequency ranges or services are to be studied.
and microwave communication systems in workplaces, hospitals, When these measurements are extended and geopositioned within a
educational institutions, both outdoors and indoors and it seems that wide area, radioelectric maps can be created indicating the distribution
Internet of Things (IOT) will boost this trend with 5G networks, services, of exposure levels to EM fields during the measuring period. Therefore,
and devices. In a near future, this might bring problems of compatibility, radioelectric maps are a spatial characterization of the EM field strength
with self and mutual interference among services and devices. or power density distribution in open or closed locations within a fre-
Because of this exponential development, a growing concern about quency range. There is a wide application of these radio maps such as
safety of EM fields is being observed in the population, institutions, interference avoidance and location, spectrum usage monitoring,
firms, local, regional, and national governments (Ro¨o¨sli et al., 2010). In human exposure to EM fields (Shan et al. 2018) or, even, in epidemio-
parallel, the scientific and technical community has stablished safe EM logical studies (Gonzalez-Rubio et al., 2016).
field exposure levels in different institutions, for both the workplace and Unfortunately, when important areas are to be mapped the number
the general public, such as the International Commission on of measurements might be too high to be cost and time effective and
* Corresponding author.
E-mail address: toni.martinez@upct.es (A. Martínez-Gonz´alez).
https://doi.org/10.1016/j.envres.2022.113577
Received 15 March 2022; Received in revised form 5 May 2022; Accepted 25 May 2022
Availableonline28May2022
0013-9351/©2022TheAuthors.PublishedbyElsevierInc.ThisisanopenaccessarticleundertheCCBY-NC-NDlicense(http://creativecommons.org/licenses/by-
nc-nd/4.0/).

A. Martínez-Gonza´lez et al. E n v i r o n m e n t a l R e s e a r c h 2 12(2022)113577
therefore the usage of propagation models and/or spatial interpolation than KG and spline in the bandwidth of 100 kHz-6 GHz.
methods are useful to estimate the electric field in those locations where All the previous works have been performed in outdoor scenarios
measurements have not been carried out. For instance, to carry out a but, to the best knowledge of authors, no evaluation of KG interpolation
radio map that evaluates the exposure levels in an environment, it is techniques has been performed to build exposure radio maps within
necessary to estimate the EMFs intensity levels within the location as a indoor facilities. In fact, there are few works that investigate interpo-
function of the spatial distribution of the measurements (de Andrade lation techniques to create indoor radio or exposure maps. Solin et al.,
et al., 2020). (2018) derive and use a Bayesian nonparametric probabilistic modeling
Many works have carried out exposure measurements and radio approach for interpolation and extrapolation of the magnetic field in the
maps in outdoor locations. The mapping of electric and magnetic field lobby of a building at the Aalto University campus in Spoo (Finland).
levels with three spatial interpolation methods: Kriging (KG), natural In this work, the point ordinary KG interpolation technique has been
neighbor interpolation (NNI) and inverse distance weight (IDW), was applied to create an indoor radio exposure map for the average electric
evaluated on an air-insulated substation supply circuit that operates at field magnitude inside the library of the Telecommunication Engineer-
230 kV/60 Hz in de Andrade et al., (2020). This work indicates that ing School at Universidad Polit´ecnica de Cartagena, Cartagena (Spain).
whereas NNI is the best interpolation method for the magnetic field, the The interpolation was based on measurements carried out with a Narda
gaussian KG method interpolate the electric field better than any other NBM-550 broadband field meter and isotropic Narda EF0691 E-field
method. In (Safigianni et al., 2009) electric and magnetic field levels probe in the frequency range 100 kHz-6 GHz. This work also assesses
have been measured at extremely low frequencies (ELF) inside an out- two methods for reducing the needed measurement locations based on
door electric power substation. the electric field intensity levels. The obtained results indicate that
Inverse distance to a power (IDP), KG, Minimum Curvature (MC), measurements in indoor locations should be prioritized at those areas
Modified Shepard’s Method (MSM) and Radial Bases Function (RBF) with higher electric field magnitude values. With this strategy, it is
interpolation methods were analyzed by using the cross-validation possible to reduce the number of locations to be measured up to a 70%
method with the electric field measurements in the central region of obtaining, in terms of both root mean square error (RMSE) and mean
the city of Mossoro´ with a frequency range from 10 MHz to 8 GHz absolute error (MAE), very similar exposure maps to that obtained with
(Santana et al., 2017). This work shows that both IDP and KG methods a regular measurement mesh.
were the ones providing the best results for interpolation. KG has been
also applied in (Paniagua et al., 2013) in an outdoor scenario where the 2. Materials and methods
results indicate that, in the urban area analyzed, the linear density of
sampling points could be reduced. 2.1. Indoor location and measurement points
Inverse Distance Weighted (IDW), spline and ordinary KG methods
have been employed in (Rufo et al., 2018) to map the electric field levels Indoor measurements were carried out at the library reading room of
for 3 a.m. emission frequencies (774 kHz, 900 kHz, and 1107 kHz) from the Telecommunication Engineering School, ETSIT, at Universidad
spectrum analyzer measurements. Authors show that the optimization of Polit´ecnica de Cartagena, in Cartagena (Spain). Latitude and longitude
the characteristic parameters of the interpolation methods allows coordinates of ETSIT are 37.598238 and (cid:0) 0.987412, respectively. Fig. 1
employing any of them, although, in this study, IDW showed the best shows the floor plan of the building and the layout of the rooms. The red
predictions. discontinuous line indicates the area where the measurements were
In (Gonzalez-Rubio et al., 2016) a personal exposimeter, Satimo EME acquired.
Spy 140 model, and ArcGis software were employed to record and map Up to 386 different locations were used to measure the average
the average exposure levels of GSM, DCS and UMTS systems in the city electric field intensity inside the reading room trying to follow a 2D
of Albacete (Spain). Other works, such as (Garcia-Moreta et al., 2019), rectangular mesh. Some locations could not be used due to fixed furni-
use machine learning regression algorithms to map and predict digital ture, mainly tables. Fig. 2 shows the points where measurements were
terrestrial television coverage in Quito (Ecuador). located.
The specific usage of the KG interpolation method to build exposure The origin of coordinates was in the lower left corner of the reading
and radio maps is described in several works. Shan et al. 2018 design a room plan. Purple symbols indicate where routers were installed. The
method of electromagnetic environment map construction based on KG total area of this room is 923.87 m2 whereas the area where measure-
spatial interpolation and the obtained results are compared to Modified ments could be performed, useable area, was 691.92 m2. Both x and y
Sheppard and IDW methods. In that work, KG obtains the minimum separation between measurement points was 0.3 m. The measurements
root-mean-square error between interpolated and measured values. were performed without any student or university personnel in-side the
Ould-Isselmou et al., (2006) use KG interpolation with external drift, library reading room to facilitate the procedure.
usually named as KED, in order to build an EM exposure map in the Therefore, the measured electric field magnitude was due, exclu-
streets of Paris for 9 bands including GSM 900, GSM 1800 and UMTS sively, to the radiating devices inside or near the location. Narrowband
downlink. Sato et al., (2019) use the KG interpolation technique to measurements have been carried out to confirm the presence of different
re-construct a radio environment map (REM). The authors conclude that sources in the environment by using a FSH4 Spectrum Analyzer from
the error in the received power estimation over log-normal channels can Rohde & Schwarz. It must be remarked that the main radiation sources
be modeled using a correlation co-efficient when the interpolation co- in the library reading room were WiFi routers accomplishing the 802.11
efficients are optimized. Additionally, in (Sato et al. 2017), ordinary g standard protocol that provide internet access to students and uni-
Kriging interpolation is employed to build a REM that allows studying versity personnel at the 2.45 GHz band. WiFi routers carrier levels were
the spatial spectrum sharing. The allowable interference power to the more than 8 dB above FM band, 12 dB above GSM band or 16 dB above
primary user is approximately calculated from the predicted distribution LTE band signals which were the most significative ones. It should be
of the estimated error. In Sato et al., 2021 authors extend the noted, however, that the proposed procedure should be independent of
Kriging-based radio map spatial interpolation to space-frequency the knowledge of the radiation sources.
interpolation and extrapolation, estimating, in this way, accurate In each location, the electric field magnitude was averaged for 6 min
radio maps on frequency bands where no (or a few) datasets are avail- (1 sample per second) and, therefore, the results shown in this work are
able with data obtained from other frequency bands. Finally, a com- a time and frequency average of the electric field magnitude.
parison of spline, IDW and KG interpolation methods of the average
electric field in-tensity in an outdoor area of Caracas (Venezuela) is
carried out in Azpurua et al. 2010) concluding that IDW performs better
2

A. Martínez-Gonza´lez et al. E n v i r o n m e n t a l R e s e a r c h 2 12(2022)113577
Fig. 1. Floor plan and layout of the rooms of ETSIT at Universidad Polit´ecnica de Cartagena, Cartagena (Spain). Discontinuous red line indicates the library reading
room where measurements were carried out. (For interpretation of the references to colour in this figure legend, the reader is referred to the Web version of
this article.)
2.2. Measurement instrumentation and procedure electric field level provided by the Narda equipment even when this
level is below the 0.2 V/m sensitivity since this helps in the imple-
Authors used Narda NBM-550 broadband field meter and isotropic mentation of the analyzed minimization procedures, which are
Narda EF0691 E-field probe to measure the average RMS E-field within explained in section 2.5.
the 100 kHz-6 GHz bandwidth. The main specifications of this
measuring set are: 2.3. Krigin interpolation procedure
• Electric Field Range: 0.2 V/m to 650 V/m Point Kriging with no drifts (ordinary Kriging) and circle search
• Linearity: ±0.5 dB space are used in this work to estimate the electric field magnitude in
• Isotropic response: ±1 dB. those points where measurements are not available. Thus, in this work
we estimate the electric field magnitude at a point from the available
Fig. 3 shows the Narda field meter and field probe at a measurement measurements of the whole data set. Equation (1) shows how the
point inside the library reading room and the height of the measure- interpolated value of the magnitude of the average electric field is
ments, which in this case was set to 170 cm. obtained:
The measurements followed the procedure indicated in the (EN
∑N
50413:2019) measurement standard. As indicated in this standard, all |E(k)| interp = w i ⋅|E(i)| measured (1)
relevant frequency components and field sources were included in the i=1
bandwidth of the used instrumentation and therefore the measurement
where |E(k)|_interp is the estimated electric field magnitude of grid
levels included the total field strength of all spectral components within
node k, N is the number of neighboring data values used in the esti-
the measurement frequency range. A preliminary survey of the indoor
mation, in this case the whole data set, |E(i)|_measured is the electric
location was carried out to identify the areas with maximum levels of
field magnitude value at location i with weight, wi. The value of weights
electric field intensity and then the measuring location matrix described
will sum to 1 to make sure there is no bias. KG interpolation method
in the previous section was defined to carry out the measurements.
calculates wi from the spatial structure of data distribution represented
It should be remarked that an important number of measurement
by a sample variogram trying to minimize the interpolation error vari-
locations showed electric field levels below the sensitivity of the device
ance (Isaaks et al., 1989). In this work, authors employed Surfer v. 16
(0.2 V/m). Several options are available when dealing with those non-
software to compute the ordinary KG interpolation estimations and to
detects, such as excluding them from the study, using the electric field
generate the interpolated surface maps (Golden Software).
value provided by the field meter, setting those measurements to zero or
0.2 V/m, assuming a statistical distribution and using fitting methods
2.4. Error estimation
with the detected data to provide estimations for these points as shown
in [Ro¨o¨sli et al., 2008], or other strategies as the ones reported in
Two different estimations were calculated for the error provided by
[Najera et al., 2020]. Each of these options will have an important
the interpolation procedure. Equations (2) and (3) show the Root Mean
impact on the obtained mean values. In this work, authors have used the
Square Error (RMSE) and the Mean Absolute Error (MAE), respectively:
3

A. Martínez-Gonza´lez et al. E n v i r o n m e n t a l R e s e a r c h 2 12(2022)113577
Fig. 2. Measuring points within the reading room of the library. Purple symbols: routers. Blue squares: areas used for mean values in Table 1. (For interpretation of
the references to colour in this figure legend, the reader is referred to the Web version of this article.)
4

A. Martínez-Gonza´lez et al. E n v i r o n m e n t a l R e s e a r c h 2 12(2022)113577
measured are set to 0 V/m and then used in the interpolation procedure.
Another important difference is that ELSP will never eliminate electric
field values with high levels because they are neighboring other points
with high electric field levels.
5. Results
5.1. Indoor measured electromagnetic map
Fig. 4 a shows the measured electric field magnitude for each of the
locations indicated in Fig. 2 and its histogram. Fig. 4 a shows that the
minimum value corresponds to the measuring point number 34 with a
field level of 0.045 V/m (5,37 μW/m2) and the maximum value corre-
sponds to the measuring point number 117 with a field level of 1.675 V/
m (7,44 mW/m2). The measurements have an average level of 0.340 V/
m (0,31 mW/m2) and a variance of 0.09 (V/m)2. In Fig. 4 b the histo-
gram for the electric field measurements is shown. From obtained data it
can be perceived that almost 55% of electric field magnitude values are
those under 0.22 V/m (0,13 mW/m2).
Fig. 5 shows the spatial distribution of the electric field magnitude
and the measuring mesh. The spatial distribution was obtained by using
the ordinary KG interpolation implemented in Surfer as described in
Section 2.C and considering all the measuring data. From obtained re-
sults in Fig. 5, one can conclude that the highest electric field magnitude
intensities are located around the routers that provide access to internet
Fig. 3. Used Narda NBM-550 broadband field meter and isotropic Narda to students and workers. Also, the electric field is intense near some
EF0691 probe (right) and height of measurements (left). windows of the reading room since the external electric field can
√̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅ propagate with less attenuation than through the building walls. It can
√
RMSE= √ √ N 1 ∑N ( |E(k)| interp (cid:0) |E(k)| measured ) 2 (2) be observed that measured levels are well below the reference levels set
i=1
1 ∑N ⃒ ⃒ ⃒ ⃒
MAE= N ⃒|E(k)| interp (cid:0) |E(k)| measured ⃒ (3)
i=1
where both RMSE and MAE are expressed in V/m.
2.5. Minimization of the number of measurement points
As explained above, a critical part of elaborating radio exposure
maps is the number of measurements that must be carried out before the
interpolation is performed. In this work two different procedures for
measurement point reduction have been proposed, implemented, and
assessed to know how they can be reduced without an important
distortion of the obtained radio exposure map. Therefore, a percentage
of the measured locations will be eliminated or set to zero depending on
the considered method and RMSE and MAE values will be obtained for
the interpolated maps.
3. Elimination of Less Significant Points (ELSP)
The method of Elimination of Less Significant Points (ELSP) consists
of evaluating a percentage of the less significant points as if they had a
value equal to 0 V/m. Once these points are set to zero, they are
considered and used during the KG interpolation procedure.
4. Geometrical Elimination of neighbors (GEN) with similar
electric field values
In the procedure of Geometrical Elimination of Neighbors (GEN) the
matrix of measurement locations is traversed and those points whose
electrical field value is closer to their neighboring points are eliminated.
Those points, consequently, are not considered during the interpo-
Fig. 4. a) Electric field magnitude levels at each measuring point within the
lation procedure. The main difference with the ELSP method is that in library reading room. Location number refers to measuring points indicated in
GEN we eliminate the points from the interpolation calculations Fig. 2 b) Histogram with cumulative percentage of measured electric
whereas for the ELSP method the points that are not considered or field levels.
5

A. Martínez-Gonza´lez et al. E n v i r o n m e n t a l R e s e a r c h 2 12(2022)113577
Fig. 5. KG interpolated spatial distribution of the electric field magnitude levels within the library reading room when using all the measurement points. Numbers
indicate the measuring point identification and location.
in (Recommendation, C. 1999, Directive, 2013/35/EU) for all the clearly degrades although it is still capable of showing the areas with
measured points. highest values of electric field magnitude. Obviously when the chosen
percentage sets to zero significant points with intermediate electric field
values, then the areas with those intermediate values, green levels, are
5.2. Reduction of measuring points
not well represented in the interpolated exposure map as it occurs for
case j).
5.2.1. Usage of ELSP strategy
However, this ELSP strategy shows that at least 70% of measuring
Fig. 6 shows the KG interpolation of the electric field magnitude
points can be skipped during the measurement procedure provided that
when different number of measuring points are used. In this case, the
the areas with highest and medium electric field values are properly
ELSP strategy was followed and 10%–90% of points were considered
sampled. Therefore, before the measurements are carried out, a pre-
zero during the interpolation. Less significant points are fix to zero in-
scanning procedure should be performed in order to locate those areas
tensity for each percentage. These points are the number of points
with maximum and minimum values. The measurement mesh should
accomplishing that percentage with lowest intensity values. Red crosses
prioritize those areas with.
indicate the points whose electric field intensity is set to zero.
Table 1 shows the Root Mean Square Error (RMSE) and the Mean
From obtained results it can be concluded that the obtained electric
Absolute Error (MAE) for the different interpolated exposure maps
field exposure maps are very similar even for the cases h) and i) where
shown in Fig. 6 following the ELSP strategy. This table shows the evo-
we have set to zero 70 and 80% points, respectively. When setting to
lution of both error indicators versus the percentage of least significant
zero 90% of least significant measurements, however, the interpolation
6

A. Martínez-Gonza´lez et al. E n v i r o n m e n t a l R e s e a r c h 2 12(2022)113577
Fig. 6. Kriging interpolated spatial distribution of the electric field magnitude levels for different percentage of used measuring points by using the ELSP strategy.
Red cross symbol indicates a point considered zero for interpolation calculations. Percentage of eliminated points are: a) 10%, b) 20%, c) 30%, d) 40%, e) 50%, f)
60%, g) 70%, h) 80%, and i) 90%. (For interpretation of the references to colour in this figure legend, the reader is referred to the Web version of this article.)
7

A. Martínez-Gonza´lez et al. E n v i r o n m e n t a l R e s e a r c h 2 12(2022)113577
points set to zero before the KG interpolation is carried out. From ob- many of them are eliminated and, therefore, the interpolation tends to
tained results one can conclude that both RMSE and MAE increase when provide electric field intensities higher than the real ones.
the number of points set to zero grows. In the same way when the In fact, when comparing the points set to zero in map 8.b and the
measuring point density is reduced then both error indicators grow. ones that are not considered in map 8.c one can deduce that too many
However, as expected, the error increase is not linear versus the per- points have been eliminated in the distorted area of map 8.c. Since this
centage of points set to zero. In fact, for percentages higher than 40% the loss of information occurs with higher electric field levels around the
interpolation error grows at higher rate than the linear behavior eliminated points, then the interpolation produces an overestimation of
observed for percentages between 10 and 30%. Three different areas the electric field.
have been considered in the room and linked to the number of sources Table 2 shows the RMSE and MAE for GEN and ELSP strategies, both
and their location. Each area is a square of 10 m × 10 m (1 Dm2) using just 50% of real measurement points for the KG interpolation
centered in the WiFi antenna. When there are walls near a WiFi trans- procedure. As expected from Fig. 8, it can be observed that GEN strategy
mitter the area is smaller in that direction. Those areas have been named for point reduction produces an interpolated map with a RMSE value
as Tx 1, Tx 2 and Tx 3 in Fig. 2. almost 3 times greater than the RMSE value provided by the obtained
It can be observed in Table 1 that near the WiFi transmitters the map after the ELSP strategy. In concordance, the MAE value after the
mean values of the electric field are slightly different from the electric GEN strategy is twice higher than the one obtained with the ELSP
field mean value within the whole room, as expected. When using all the approach.
measurements for interpolation, the mean values of areas near the
transmitters are higher but these values tend to level when using less 6. Discussion
points for interpolation. Also, reducing the density of points for inter-
polation with the ELSP strategy produces an increment of the mean In this work it has been shown that KG interpolation technique can
values both at the whole measuring area and within the areas near the be applied to create an indoor exposure map for the average electric field
transmitters. magnitude inside a university library with routers working in the 2.45
Fig. 7 shows the RMSE and MAE indicators for the interpolation GHz band. A quasi-regular mesh for measuring points has been used
versus the per-centage of points set to zero before the KG interpolation is with a measuring density around 0.418 measurements per square meter.
carried out. It can be observed a linear behavior for both RMSE and MAE The obtained exposure map showed that all the electric field levels were
when this percentage ranges from 10 to 30% but then the error grows in below the limits set by the international standards (Recommendation,
an exponential way with higher rates than the first linear behavior. The 1999, Directive, 2013/35/EU).
reason for this may be the following: when a low percentage of points The obtained results in Figs. 4 and 5 show that, as it usually happens
are set to zero the error is not very big because in the ELSP strategy the with exposure maps, electric field levels are much higher at those areas
points with lowest intensities are the first ones to be eliminated. How- close to the radiation sources, routers in this case, whereas the rest of
ever, as the percentage grows the error is higher because the measured areas show electric fields near zero V/m. In fact, the histogram in Fig. 4 b
intensity is not as low as previously eliminated points. Thus, the more shows that electric field intensities ranging from 0.07 to 0.52 V/m
points you set to zero, the higher the error increase rate. provide a cumulative probability around 70%, being therefore the most
frequent values as perceived in Figs. 4 and 5.
5.2.2. Usage of GEN strategy Obtaining such a measurement required 38.6 h distributed in a three-
Fig. 8 shows a comparison of three exposure maps obtained with KG day measurement period and, therefore, it is obvious that there is a need
interpolation under the following conditions: a) with no measuring for measurement point reduction procedures maintaining, at the same
points being eliminated or set to zero, b) setting to zero 50% of the time, the accuracy and validity of the exposure map when interpolating.
measuring points according to ELSP strategy and c) eliminating 50% of In this work, we have proposed and assessed two different strategies to
measured points by using GEN methodology. From obtained results it reduce measuring points before the KG interpolation is carried out: ELSP
can be observed that maps 8.a) and 8.b) show very similar electric field and GEN.
spatial distributions with slight differences for some areas with electric Fig. 6 shows that ELSP strategy can reduce up to 70% the measure-
field levels around 0,7 V/m. However, map 9.c, obtained with the GEN ment points versus a regular mesh strategy. In this strategy, we set to
strategy, shows a great exposure map distortion, mainly inside the black zero those low intensity electric field points where measurements are
dotted line square. not considered, and this approach provides very similar exposure maps
This happens because GEN approach eliminates those points whose to those ones generated with a regular mesh and produces low RMSE
neighbors have the closest electric field values. Since there are many and MAE values. The reason for this success is that most electric field
points in the measuring mesh with low electric field intensity values, levels (around 70% as indicated by the histogram in Fig. 4b) are close to
zero.
The usage of GEN procedure, however, is not successful and provides
much higher RMSE and MAE errors than ELSP. In fact, this methodology
is not even capable of reducing measurement points to a half as shown
both in Fig. 8 and Table 2. The problem of this strategy is that it elim-
inates those points like their neighbors in terms of electric field
magnitude. Since the majority of points have low intensity values, GEN
method will overestimate the electric field in those areas where low
intensity values are close to mid or high intensity values.
It is also important mention that results have been obtained for the
site under consideration, and the instrumentation used for the acquisi-
tion of E-field data described in the previous sections. Less than a 20% of
the got values are below the detection threshold and maximum values
are way above it. This point should be considered for measurements
taken with an instrumentation with a different detection threshold or a
Fig. 7. RMSE and MAE evolution versus the percentage of points set to zero in scenario with a different number of emitting sources and powers.
the ELSP strategy before the KG interpolation is carried out. Dotted lines Procedure for the reduction of points in indoor exposure maps
indicate the linear behavior shown by RMSE and MAE for low percentages. From obtained results it seems clear that measurements in non-
8

A. Martínez-Gonza´lez et al.                                                                                                                                                                               E n  v  i r o  n  m  e  n  t a l  R  e  s e  a r  c h   2 12(2022)113577
Fig. 8. Comparison of three electric field exposure maps obtained with KG interpolation: a) using 100% of measuring points, b) reduction of 50% of points by using
ELSP strategy, c) reduction of 50% of points by using GEN strategy.
Table 1
Mean values, Root Mean Square Error (RMSE) and the Mean Absolute Error (MAE) for the different interpolated exposure maps shown in Fig. 6 following the ELSP
strategy.
Percentage of points set to  Meas. density (pts/  Employed points for  Mean values  RMSE (V/  MAE (V/
| zero  | Dm2)  | interpolation  |                    |                     | m)  m)        |
| ----- | ----- | -------------- | ------------------ | ------------------- | ------------- |
|       |       |                | Room (V/  Tx 1(V/  | Tx 2 (V/  Tx 3 (V/  |               |
|       |       |                | m)  m)             | m)  m)              |               |
| 0%    | 42    | 386            | 0,348  0,418       | 0,491  0,478        | 0,000  0,000  |
| 10%   | 38    | 348            | 0,377  0,379       | 0,506  0,478        | 0,043  0,028  |
| 20%   | 33    | 309            | 0,409  0,471       | 0,506  0,501        | 0,045  0,031  |
| 30%   | 29    | 271            | 0,448  0,502       | 0,521  0,543        | 0,045  0,035  |
| 40%   | 25    | 232            | 0,496  0,537       | 0,521  0,632        | 0,049  0,041  |
| 50%   | 21    | 193            | 0,561  0,579       | 0,542  0,691        | 0,054  0,050  |
| 60%   | 17    | 155            | 0,647  0,687       | 0,617  0,809        | 0,061  0,058  |
| 70%   | 13    | 116            | 0,749  0,796       | 0,743  0,917        | 0,071  0,067  |
| 80%   | 8     | 78             | 0,866  0,866       | 0,806  0,988        | 0,091  0,081  |
| 90%   | 4     | 39             | 1,080  1,159       | 1,016  1,125        | 0,119  0,094  |
High and medium values, skipping those areas where minimum values are sensed during the pre-scanning procedure. In this way measurement and post-processing
time could be reduced up to a 70% with similar results for the obtained interpolated map.
4. Travelling along the regular mesh and avoid measurements at points
Table 2
with an electric field level less than 30% of the maximum field level
Root mean Square Error (RMSE) and the Mean Absolute Error (MAE) for the
measured. Therefore, only those points whose electric field level is
obtained maps using GEN and ELSP strategies for the reduction of measuring
higher than this established thresh-old level shall be fully measured.
points. Both strategies use 50% of real measuring points to generate the exposure
5. Assigning a zero level to those points in the regular mesh where
map.
measurements are not performed.
Percentage of points  Point  Employed points  RMSE  MAE  6. Calculating the interpolation of measured data according to the
| eliminated (GEN) or  | reduction  for interpolation  | (V/m)  (V/m)  |     |     |     |
| -------------------- | ----------------------------- | ------------- | --- | --- | --- |
desired interpolation method.
| set to zero (ELSP)  | strategy              |                |                |     |     |
| ------------------- | --------------------- | -------------- | -------------- | --- | --- |
| 50%                 | GEN  193              | 0,184  0,103   |                |     |     |
| 50%                 | ELSP  193 (non zero)  | 0,066  0,050   | 7. Conclusion  |     |     |
In this work, authors have applied for the first time the KG inter-
regular meshes can be used for the reduction of points in indoor electric-  polation procedure to create an electric field indoor exposure map. This
field radio maps without a degradation of the interpolated map. How- map has been conducted inside a reading room of the library of the
ever, the measurement mesh should be finer in those areas where the  Telecommunication Engineering School at Universidad Polit´ecnica de
electric field magnitude shows higher levels. Therefore, the following
Cartagena. The obtained results along a regular mesh with 386 mea-
procedure could be followed to reduce the number of measuring points
surements indicate that electric field levels are well below the stablished
that allow the representation of an accurate exposure map according to
limits in international standards and that most measured levels are close
ELSP strategy:
to zero V/m.
Two different procedures for the reduction of measuring points have
1. Perform a fast scan of the indoor facilities and locate those areas
been presented and evaluated: ELSP and GEN. During ELSP evaluation,
where maximum levels are detected.
those points of the regular mesh with lower electric field magnitude
2. Definition of maximum level inside the indoor area to be measured.   values are set to zero and then KG interpolation is carried out. The re-
3. Creation of a regular mesh that includes those areas with maximum  sults indicate that up to 70% of the regular mesh can be eliminated
electric field levels.   without a noticeable distortion of the generated map.
9

A. Martínez-Gonza´lez et al. E n v i r o n m e n t a l R e s e a r c h 2 12(2022)113577
GEN, however, eliminates the percentage of points whose neighbors Golden Software (accessed on 30th of October, 2021). https://www.goldensoftware.
have the most similar electric field levels and this eliminated points are com/products/surfer.
Gonzalez-Rubio, J., Najera, A., Arribas, E., 2016. Comprehensive personal RF-EMF
not considered for the KG interpolation. The results show that the exposure map and its potential use in epidemiological studies. Environ. Res. 149,
interpolated maps after applying GEN methodology are distorted even 105–112.
when eliminating only 50% of the points in the regular mesh with much ICNIRP, 2020. International Commission on Non-Ionizing Radiation Protection, May
2020. Guidelines for limiting exposure to electromagnetic fields (100 kHz to 300
greater RMSE and MAE values than ELSP strategy.
GHz). Health Phys. 118 (5), 483-524. https://doi.org/10.1097/
Therefore, a procedure for discarding measuring points of a regular HP.0000000000001210.
mesh based on the results obtained in this work is provided by using the IEEE, 2019. IEEE Standard for Safety Levels with Respect to Human Exposure to Electric,
Magnetic, and Electromagnetic Fields, 0 Hz to 300 GHz - Redline. IEEE, 1-Accessed:
ELSP strategy. This could save time for elaborating exposure maps while
Jun. 15, 2021. [Online]. Available:https://ieeexplore.ieee.org/servlet/opac?
maintaining map accuracy. Although these conclusions have been ob- punumber=89304192019.
tained for indoor conditions, they could be extrapolated or adapted to Isaaks, E.H., Srivastava, R.M., 1989. Ordinary Kriging. In: Applied Geostatistics. Oxford
university press, New York, pp. 278–322. United States of America.
outdoor radio and exposure maps provided that the histograms of
Itu-T Recommendation, K., 2014. 100: ’Measurement of Radio Frequency
measurements are similar to the ones shown here. Electromagnetic Fields to Determine Compliance with Human Exposure Limits when
a Base Station Is Put into Service.
Najera, A., Ramirez-Vazquez, R., Arribas, E., Gonzalez-Rubio, J., 2020. Comparison of
Credit author statement
statistic methods for censored personal exposure to RF-EMF data. Environ. Monit.
Assess. 192, 77. https://doi.org/10.1007/s10661-019-8021-z.
A. Martínez-Gonz´alez: Resources, Supervision, Project administra- Ould Isselmou, Y., Wackernagel, H., Tabbara, W., Wiart, J., 2006. Geostatistical
tion, Methodology, Writing – review & editing, J. Monzo´-Cabrera: interpolation for mapping radio-electric exposure levels. Proc. EuCAP 1, 1–6. Nice,
France, 6-10 November 2006.
Writing – review & editing, Visualization; A.J. Martínez-Sa´ez: Data Paniagua, J.M., Rufo, M., Jimenez, A., et al., 2013. The spatial statistics formalism
curation, Conceptualization, Validation; A.J. Lozano-Guerrero: Investi- applied to mapping electromagnetic radiation in urban areas. Environ. Monit.
gation, Writing – review & editing Pinh A ei s r s o e , s s F . . , 1 M 85 a , r a 3 n 1 h 1 ˜a – o 3 , 2 T 2. . , h B t e tp rn s: a / r / d d o o i F .o il r h g o / , 1 M 0. . 1 , 0 e 0 t 7 a / l. s , 1 2 0 0 6 1 6 5 1 . - 0 A 1 s 2 se -2 ss 5 m 55 en -7 t . of non-ionizing
radiation from radio frequency energy emitters in the urban area of Natal city,
Brazil. Sci. Res. Essays 10 (2), 79–85. https://doi.org/10.5897/SRE2014.6025.
Declaration of competing interest
Recommendation, C., 1999. Council Recommendation of 12 July 1999 on the Limitation
of Exposure of the General Public to Electromagnetic Fields (0 Hz to 300 GHz).
The authors declare that they have no known competing financial Communities 59-70.
Ro¨o¨sli, M., Frei, P., Mohler, E., Braun-Fahrl¨ander, C., Bürgi, A., Fro¨hlich, J.,
interests or personal relationships that could have appeared to influence
Neubauer, G., Theis, G., Egger, M., 2008. Statistical analysis of personal
the work reported in this paper. radiofrequency electromagnetic field measurements with nondetects.
Bioelectromagnetics 29, 471–478. https://doi.org/10.1002/bem.20417.
Ro¨o¨sli, M., Frei, P., Mohler, E., Hug, K., 2010. Systematic review on the health effects of
Acknowledgment exposure to radiofrequency electromagnetic fields from mobile phone base stations.
Bull. World Health Organ. 88, 887–896G. https://doi.org/10.2471/BLT.09.071852.
This research did not receive any specific grant from funding Rufo, M., Antolín, A., Paniagua, J.M., Jim´enez, A., 2018. Optimization and comparison
of three spatial interpolation methods for electromagnetic levels in the AM band
agencies in the public, commercial, or not-for-profit sectors. within an urban area. Environ. Res. 162, 219–225.
Safigianni, A.S., Tsompanidou, C.G., 2009. Electric- and magnetic-field measurements in
References an outdoor electric power substation. IEEE Trans. Power Deliv. 24 (1), 38–42.
Santana, T.A.A., de Andrade, H.D., Queiroz Júnior, I.S., Tavares da Silva, I.B., 2017.
Comparison of spatial interpolation methods to determine exposure ratio to electric
Azpurua, M., Dos Ramos, K., 2010. A comparison of spatial interpolation methods for fields in urban environments. Electron. Lett. 53 (18), 1250–1252.
estimation of average electromagnetic field magnitude. Progr. Electromagnetics Res. Sato, K., Fujii, T., 2017. Kriging-based interference power constraint: integrated design of
M 14, 135–145. the radio environment map and transmission power. IEEE Trans. Cogn. Commun.
Cleveland, R.F., Ulcek, J.J.L., 1999. Questions and answers about biological effects and Netw. 3 (1), 13–25.
potential hazards of Radiofrequency electromagnetic fields. Off. Eng. Technol. Fed. Sato, K., Inage, K., Fujii, T., 2019. Modeling the Kriging-aided spatial spectrum sharing
Commun. Comm 36. over log-normal channels. IEEE Wirel. Commun. Lett. 8 (3), 749–752.
de Andrade, H.D., de Figuˆeiredo, A.L., Fialho, B.R., da, S., Paiva, J.L., de, S., Queiroz Sato, K., Suto, K., Inage, K., Adachi, K., Fujii, T., 2021. Space-frequency-interpolated
Júnior, I., Sousa, M.E.T., 2020. Analysis and development of an electromagnetic radio map. IEEE Trans. Veh. Technol. 70 (1), 714–724.
exposure map based in spatial interpolation. Electron. Lett. 56 (8), 373–375. Shan, J., Shao, W., Xue, H., Xu, Y., Mao, D., 2018. The method of electromagnetic
Directive, 2013. /35/EU of the European Parliament and of the Council of 26 June 2013 environment map construction based on Kriging spatial interpolation. July 6-8. In:
on the Minimum Health and Safety Requirements Regarding the Exposure of Proceedings of the International Conference on Information Systems and Computer
Workers to the Risks Arising from Physical Agents (Electromagnetic Fields). Aided Education (ICISCAE). IEEE, Changchun, China, pp. 212–217. IEEE, Piscataway
En 50413, 2019. Basic Standard on Measurement and Calculation Procedures for Human (New Jersey), USA.
Exposure to Electric, Magnetic and Electromagnetic Fields (0 Hz - 300 GHz). Solin, A., Kok, M., Wahlstro¨m, N., Scho¨n, T.B., S¨arkk¨a, S., 2018. Modeling and
Garcia-Moreta, C.E., Camana-Acosta, M.R., Koo, I., 2019. Prediction of digital terrestrial interpolation of the ambient magnetic field by Gaussian processes. IEEE Trans.
television coverage using machine learning regression. IEEE Trans. Broadcast. 65 Robot. 34 (4), 1112-112.
(4), 702–712.
10
