# Sega NN GNO Exporter
A Blender plugin that exports a Sega NN GNO model file designed for Sonic Riders (GameCube).

## Requirements

- Blender 3.1 or above.

## Installation

1. Get the plugin from the [releases](https://github.com/Sonic-Riders-Tournament-Edition/sega-nn-gno-exporter/releases) page.
2. In Blender, go to Edit > Preferences > Add-ons and click the Install... button at the top right corner of the window.
3. Select the downloaded plugin's .zip file in the file browser.
4. Once that's done, make sure to put a tick in the checkbox of the plugin, so that the plugin gets enabled.

## Usage

### Features

- A new button under File > Export, for exporting a complete model file:
  - Format:
    - Currently only has options to export Character Model files and Spline files. The "Splines" option is extremely experimental and unfinished, so don't use this. Use only the "Character Model" option for exporting character models. You can also use this option to export general use models.
  - Model Type:
    - Contains multiple options that allow you to specify the type of your model. Has options for character models, board only models, general use models and an option for no rig to be included in the final model file. 
  - Include texture list:
    - For character models, this checkbox needs to be ticked. There are only very specific circumstances where this box isn't ticked.
  - Use bone data from other model:
    - You can use this to specify another Sega NN GNO model file to take rig/bone data from. Keep in mind, the file has to be in the same directory as the directory you're exporting the model to for it to work.
  - Raw bone data:
    - Tick this checkbox if the file you are specifying only has bone data in it and nothing else, otherwise if you are specifying another model file, keep this unticked.
  - Filename:
    - The name of the file to be used with the two options above. Has to be in the same directory as the export directory.

- A new section under Object Data Properties for meshes, GNO Mesh Properties:
  - Create Vertex Groups:
    - This button is used to create all usable vertex groups on the current mesh's armature. This is for if you just want to look through all of the bones you can use when assigning meshes/weight painting. You don't have to have all of these vertex groups present on the mesh for the export process to work.
  - Use custom bone visibility / Custom bone visibility:
    - This setting is for advanced users. Usually used in tandem with the "No Rig" model type export option.
  - Rename Vertex Groups (Prefix):
    - **NOTE:** Keep in mind that this only renames vertex groups and not the rig's bones!
    - Prefix: Sets the prefix to be applied to the vertex group names. Usually, with Sega NN Tools, the imported rig's bones are named something like `snc07_Bone_0003`. This is useful for if you switch the rig you're using, and want a quick way to rename all of your vertex groups. If you were to set the prefix property to `nuc03` for example, it would rename the vertex groups to `nuc03_Bone_0003`.
    - Rename Current Mesh Vertex Groups: Renames all the vertex groups on the mesh you have selected only.
    - Rename All Vertex Groups: Renames all the vertex groups on all meshes in the scene.
  - Rename Vertex Groups (Add/Remove Leading Zeroes):
    - **NOTE:** Keep in mind that this only renames vertex groups and not the rig's bones!
    - Sometimes, the imported rig's bones can be named something like `snc07_Bone_3` instead of `snc07_Bone_0003`. These sets of features deal with renaming that part of the vertex groups.
    - Add Leading Zeroes: Adds zeroes in front of the bone number. It transforms it from `snc07_Bone_3` to `snc07_Bone_0003` for example.
    - Remove Leading Zeroes: Removes zeroes in front of the bone number. It transforms it from `snc07_Bone_0003` to `snc07_Bone_3` for example.
    
- A new section under Material Properties for meshes, GNO Material Properties:
  - Disable backface culling:
    - By default, backface culling is enabled on materials in the game. Use this option to disable it, if needed.
  - Always on top:
    - This makes it so that the meshes with this material assigned will always render on top of everything else in the model.
  - Fullbright:
    - Makes the shading on meshes with this material assigned a lot more brighter all around and less reliant on normals/shading.
    
- A new tab for Image Texture nodes in the Shader Editor, GNO Properties:
  - Texture Properties:
    - None: Uses the texture in this texture node as a regular diffuse texture.
    - Reflection Texture: Uses the texture in this texture node as a reflection texture.
    - Emission Texture: Uses the texture in this texture node as an emission texture.
    
## Exporting a model for Sonic Riders TE 2.0

To make this process as streamlined as possible, you should use the versatile toolkit for all Sonic Riders related stuff by Sewer56, found [here.](https://github.com/Sewer56/SonicRiders.Index)

For importing already existing models in the game into Blender, you should use Arg's [Sega NN Tools.](https://github.com/Argx2121/Sega_NN_tools)

For converting textures into the correct format for the game, you should use [PuyoTools.](https://github.com/nickworonekin/puyotools)

This entire guide will be using the aforementioned resources to put a model into the game. When talking about game files, the guide will be referencing files currently present in Sonic Riders Tournament Edition 2.0.

### Setting up the basis for exporting

Firstly, you should extract all of the game's files from the ISO into a folder for ease of access and modification. 
To do this, right click on the game in your Dolphin library, go to Properties > Filesystem. Right click on Disc at the top and select Extract Entire Disc. This will allow you to choose a folder to extract all the files into which you can also boot up in Dolphin afterwards.

The setup of the model files starting from TE 2.0 has been altered from base game. 
The board models have been separated from the character models into the following naming convention: `P?00` for the character's default board model, the character models into the following naming conventions: `P?CO` for characters on board models, `P?CB` for characters on bike models, and `PB##` for all other board models, where the `#` is replaced with a gear's model number.
Super form models and skate models are still all one model, and follow the base game naming convention.
The `?` in these naming conventions are replaced with a letter corresponding to a character found in this table:

| Character | Letter |
|---|---|
| Sonic | S |
| Tails | T |
| Knuckles | K |
| Amy | A |
| Jet | J |
| Storm | M |
| Wave | W |
| Eggman | E |
| Cream | C |
| Rouge | R |
| Shadow | D |
| Super Sonic | P |
| NiGHTS | 0 |
| AiAi | 1 |
| Ulala | 2 |
| E10G | Z |
| E10R | O |
| Silver | 3 |
| Metal Sonic | 4 |
| Emerl | 5 |
| Blaze | 6 |
| Chaos | 7 |
| Tikal | 8 |

In TE 2.0, there exists a dynamic character slot that opens up whenever it detects a model file for it in the ISO. It uses Shadow as a base, which means that if you want to export a model into that slot, you should export via importing Shadow's character model into Blender, and using his rig (theoretically you can use anyone's rig except for Eggman's, and just edit it to your liking). 
Otherwise, if you are replacing another model, import that character model into Blender and use their rig instead. Make sure to choose the correct model type option when exporting, which would be the Character model type (unless you are actually replacing Eggman, then use the one specifically for him).
This dynamic character slot's default board model file is named `PX00` and the character model file should be named `PXCO`, which is not present in base TE 2.0, thus why the character slot is locked by default.

For this example, we'll be exporting into that dynamic character slot, so we'll be importing Shadow's character model. The corresponding file for that would be `PDCO`. 
We'll be using the Riders Archive Tool from Sonic Riders Index to extract all the files from this archive file. You could probably keep this folder for later for when you want to repack it with your own character model.

Upon extracting, we'll get two folders. `000_00000`, which contains the character's model file (`00000`), and the character's texture archive file that is associated with the model (`00001`).
You don't have to worry about the `001_00009` folder, as that folder contains the files for the shadow below the character. Before importing the character model file into Blender, it should be named from `00000` to something that has the `.gno` extension at the end, like `Shadow.gno` for example.
This makes it so that the model imports correctly into Blender.

If you wish to export a board or bike model only, you don't need to import any sort of character model. More on that in the [Board models](#board-models) section.

### Setting up your own model

Now that you have a pre-existing rig imported into Blender to work with, you can now start putting your own stuff in there. Here are a few key points to keep in mind for what exactly is exported into the model:
- Every single mesh in the scene will be exported. This *doesn't* include all of the meshes present in the Blender file itself.
- Every single material in the *entire* Blender file will be exported. This means *all* of the materials present in the Blender file, even if they aren't used anywhere.
You can manage all of the contents of the Blender file via the Outliner and setting the Display Mode to Blender File.

Furthermore, here are some points/limitations you need to follow when setting up your model:
- When weight painting meshes, you **have** to make sure that every vertex on the mesh only has a maximum of 2 vertex groups assigned to it. *The exporter doesn't currently support any more than that and only takes the first two vertex groups it sees if you go over this limit.* Furthermore, make sure that every single vertex has a group assigned to it.
- A mesh must only have one material assigned to it.
- For meshes that are supposed to be just parented fully to a single bone without any weight painting, the mesh must only contain *one* vertex group with the name of the bone it's supposed to be assigned to.
- **NOTE:** Currently, the latest version of the exporter has a bug that doesn't properly account for meshes that don't have custom split normal data set. This means that you **have** to make sure Auto Smooth is turned on for the mesh and that custom split normal data is properly set. Otherwise, the shading of the exported model will be broken.
- All the meshes in the scene have to be parented to the Armature.
- Don't make textures that are high resolution. An optimal texture resolution is 128x128. Generally, don't go too much over 256x256. Furthermore, texture resolutions must be a power of 2.
- Don't make models that are too much over a tri count of about 6,000. This is to make sure it's optimized enough for the GameCube to run it.

#### Board models

For board or bike models, you do not need to import a rig or original game model of any sort. This means that half of the points mentioned in the [Setting up your own model](#setting-up-your-own-model) section do not apply. All you need is your board model in Blender, material correctly assigned to it and you're golden (obviously leave the vertex groups of the mesh empty or you will confuse the exporter). The exporter will take care of the rest to ensure it works in game.

#### Rig editing

You can make slight edits to the rig you import from one of the game's models to fit your character model more as you see fit. There are limitations to how you can edit a bone on the rig though. You are only allowed to change the position of the **entire** bone. This means you cannot edit the rotation of the bone, the scale of the bone, and the head or tail of the bone separately as that also changes the rotation of the bone technically. This is because if you rotate a bone in other ways than how it is on the original rig, the animations in the game are not going to be compatible. So, only moving the entire bone around to fit your character is all you can do to preserve compatibility.

*If you notice your model being sort of broken (so not a complete vertex explosion) in the game, there's a high chance you edited the rig wrong or you assigned your meshes to incorrect bones.*

**NOTE:** If you wish, you can use a script provided by Sewer56 and Arg that renames all of the bones on the rig, so you know which bone is what. You can find the script [here.](https://sewer56.dev/SonicRiders.Index/guides/custom-models.html#renaming-bones)

#### Materials

There are certain properties you are able to control about materials via the Shader Editor. 
The exporter takes the color of a material from a RGB node, the opacity of a material from a Value node and the textures from Image Texture nodes of course.
The nodes don't have to be necessarily connected to anything, they just have to be present in the material and the exporter will use them.

You can also use Emissive and Reflective textures on your model. For this, you have to go into the properties of the texture node in your Shader Editor, where you will see a new section for GNO specific properties. You can set your texture type from there if necessary. By default, every texture node is a diffuse texture.

#### Miscellaneous points

There is a chance that your exported model will be rotated weirdly when exported into the game. 
This is because the models in the game aren't exported with them standing up like you see them when you first import the model into Blender.
The game rotates all the character models 90 degrees upwards by the X axis (for some reason), so this is something to account for when exporting your model.
You can see this in action, as the imported model's armature is rotated 90 degrees on the X axis.

### Exporting your model

Once you have everything set and ready to go, you can now export the model via File > Export. 
For this example, since we are exporting into the dynamic character slot, we'd just have to change the Model Type to `Character`, and make sure the Format is `Character Model` and `Include texture list` is ticked.
Upon exporting, the order of the texture files that are required by the model will be printed out to the system console of Blender.
You can access the system console via Window > Toggle System Console.
The order in the console is the exact same order you have to construct the texture archive in, otherwise the model file will reference the wrong textures on materials.
For texture nodes in materials that didn't have a texture file assigned to them, they'll be named as `untitled.gvr`.

### Constructing the texture archive

To construct a texture archive, your textures must first be converted into a format the game can read. This can be done via PuyoTools. 
In PuyoTools, select Texture > Encode. The texture format must be GVR. The format settings have to be as follows:
- Data Format: DXT1 Compressed
- Global Index: 0, GCIX
- Has Mipmaps must be ticked

Under General Settings, make sure Compress Texture is set to No.

Once you have all of your textures converted, you can construct the texture archive using those converted files with the order you got from exporting the model.
This can be done via the Riders Texture Archive Tool in Sonic Riders Index.

### Repacking the final archive file

The files you created in the last few sections, namely the character model file and the texture archive file, must be named accordingly in the final model archive file.
The exported .gno model file must be renamed to `00000` and the texture archive file must be renamed to `00001`.
These files then must be put into the `000_00000` folder of the model archive file you extracted earlier using the Riders Archive Tool.
Once you replace those files, you may pack it all back into one file using the Riders Archive Tool.
Once you have the final archive file, rename it to `PXCO` and put it in the game files folder.
Upon launching the game through Dolphin, you'll find a character slot next to Tikal's slot has been unlocked, in which your character model resides.

## Contributions

All sorts of contributions are welcome. The current state of the exporter is fairly inoptimized and missing features that I don't know how to implement myself, so it'd be very much appreciated!

