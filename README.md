# gimp-scan-cutter
GIMP python plugin to cut out scanned photos/documents from a single image

This plugin is a complete rewrite of Script-fu plugin https://github.com/dmig/DivideScannedImages. For the moment it repeats original plugin functionalities and flaws.

## To make it run, you’ll have to
* Download and install the latest version of **GIMP** http://www.gimp.org/downloads/
* (Optionally) Build and install _gimp-deskew-plugin_ https://github.com/dmig/gimp-deskew-plugin
* Download [gimp-scan-cutter.py](https://raw.githubusercontent.com/dmig/gimp-scan-cutter/master/gimp-scan-cutter.py) and put it to the GIMP plug-ins folder.
    * On linux run `wget https://raw.githubusercontent.com/dmig/gimp-scan-cutter/master/gimp-scan-cutter.py -O $HOME/.config/GIMP/2.10/plug-ins/` to install
    * On Windows save file to `plug-ins` directory under GIMP installation directory (like C:\Program Files\GIMP 2\share\gimp\2.0\plug-ins) or under user GIMP directory
* Restart GIMP. You should now see the "Scan cutter" submenu listed at the bottom of the "Tools" menu with 2 items: 'Cut out photos...' and 'Batch cut out photos...'.

## Tips
* Unlike Adobe Photoshop, this plugin gives you some choice on how you want it to behave.
    * Many of these settings should be self-explanatory.
    * Important is that your scanned images have a consistent region that represents the “background color”. Typically this would be the corners of your scanned image.
    * The background colour can best be determined automatically via the specified offset from one of the corners. However, a background colour may also be manually defined via supplied colour picker
    * If _gimp-deskew-plugin_ is not found to be present by the script, the "Run Deskew" option will have no effect

Feel free to experiment with the settings, especially:
* **Selection Threshold** which controls how sensitive the background color is defined in terms of separating it from the foreground photos.
* **Size Threshold** which controls the minimum size of any of the sub-images (rejects smaller items as noise)
* **Max number of items** which specifies the maximum number items to be extracted from a single page.
* In the batch mode the **Source directory** points to the folder of input scanned pages, and the **Target directory** to a (preferrably empty) directory that will contain the output.
* The **Save file suffix** specifies the suffix that will be used for each output file, which is also sequentially numbered. E.g. `Image_003.jpg` cut outs would be named `Image_003-Crop-01.jpg`, `Image_003-Crop-02.jpg`, `Image_003-Crop-03.jpg`, e.t.c.

Click on OK, and watch it run through your scanned image(s).

Comparing this solution to Photoshop's built-in filter surprised Francois Malan, in that this homebrew filter seemed to be much more reliable, even straight out of the box. It is also possible to customise the filter’s behavior to suite your specific stack of scans.

Note, however, that **gimp-scan-cutter** can and will fail for difficult cases. Here are some more tips you should follow to maximize your chances of success:

* The photos should not overlap or touch each other. If they do, they will not be divided from each other by the automatic script
* The scanned page should be cropped in such a way that the to-be-identified items don't extend beyond the page background, and the page background should extend up to or beyond the image borders
    * e.g. – seeing the wooden floor (on which an album was placed while photographing it) will confuse the algorithm unless you carefully set up the “Background Sample X/Y offset” values.
* The page background should be uniform (white or black are good), and have enough contrast relative to the photos
* The page (including the background) should be evenly lit

## History
* Based on a script originally by Rob Antonishen http://ffaat.pointclark.net
* This script was originally posted here http://registry.gimp.org/node/22177
* Francois Malan written a blog post http://francoismalan.com/2013/01/how-to-batch-separate-crop-multiple-scanned-photos/ explaining its usage
* I forked his [code](https://github.com/FrancoisMalan/DivideScannedImages) to https://github.com/dmig/DivideScannedImages, fixed some bugs and made script running on GIMP 2.10
* Later I made this Python-fu version, which I plan to maintain.
