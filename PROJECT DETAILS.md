PROJECT DETAILS



What DragonScan is about



The problem. People usually judge dragon fruit by looking at the peel: colour, spots, defects. But a fruit can look fine outside while its flesh is already soft, translucent or rotting. Cameras, including existing systems like Cometa et al. (2025), only see the peel, so they can't fully catch this hidden degradation.



Your idea. Add a sensor that can sense beneath the peel. A 60 GHz FMCW radar sends signals into the fruit, and the reflection changes with water content and tissue condition. Combining the radar with a camera might detect degradation that the camera alone misses.



Main goal



To build and test DragonScan, a low-cost IoT scanning station that photographs a dragon fruit and scans it with radar without cutting it, then predicts whether its flesh is degraded.



It uses a camera with YOLOv11 and EfficientNet-B0 for detection and classification, together with an FMCW radar sensor that reads the fruit's internal properties. 

To work properly, our system needs a physical setup, so we are looking for help fabricating \[the part, e.g., a frame that holds the camera and radar sensor above the fruit]. 

It must hold the camera and radar at a fixed height and angle, keep the fruit steady during scanning, and be stable, easy to assemble, and easy to carry for testing.



**Raspberry Pi 5 (8GB):** the edge controller. It triggers the camera and radar, pairs each photo with its radar reading under one scan ID, and sends the record to your laptop over Wi-Fi.



**Camera Module 3:** takes the exterior photo of the fruit for Model V (EfficientNet-B0). Its focus, exposure and white balance can be locked, so every photo is taken the same way.



**Pi 5 camera cable (22-pin to 15-pin):** connects the camera to the Pi 5. The cable that comes with the camera doesn't fit the Pi 5.



**Infineon radar kit (BGT60TR13C, 60 GHz FMCW):** sends radar chirps at the fruit and records the raw reflected signal, which carries information from beneath the peel. This feeds Model R (XGBoost).



**27W USB-C power supply:** powers the Pi 5, and through it the camera and radar.



**microSD card:** holds Raspberry Pi OS and your capture software.



**USB cable:** connects the radar kit to the Pi for power and data.



**Pi case:** protects and cools the Pi. The 3D-printed hood now does this job, so you can skip the ₱499 case and add the official Active Cooler (₱716) for cooling instead.

