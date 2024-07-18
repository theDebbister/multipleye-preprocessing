stimuli are generated as images, AOI are defined before experiment starts 
storing as csv files

Raw samples
 aoi schon mappen? Kann man aber braucht halt ultra viel speicher
 raw trial ebene und dann eine methode, um die zu mergen
 eher nicht normalized, es gibt aber die methode, beschreiben wann man normalisieren soll und wann nicht
 alles, was sich pro session oder pro trial, text wiederholt in eine separate file, aber jeweils eine methode, um das dann zu mergen
 aoi files sind lab spezifisch und nicht nur sprachspezifisch!! Make naming according in experiment
 tokenisierung muss es für alle sprachen geben
 aoi files gibt es bei pymovements schon, aber das mapping noch nicht 
·      Aoi auch bei fixations abspeichern
·      Metadaten welches auge pro trial, kann sich ja nicht ändern innerhalb eines trials
·      Data quality  blink detection native, optical artifact detection, ratio von fixation on stimulus und nicht on stimulus, automatische calibration metrik (Davids fixation correction, overlap of corrected und uncorrected)?
·      Wollen wir vollautomatische fixation correction einbauen?  einfach methods zur verfügung stellen, sollte aber sehr prominent sein
·      Merge their own aois, e.g. definiert aois mit delimiter im text und dann können wir das mit diesem delimiter mergen
·      Main sequence plots machen  gibt’s aber schon in pymovements
