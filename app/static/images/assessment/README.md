# Puzzles Challenge — Assessment Images

This quiz's images live in the Google Drive account that owns the source Google
Form ("Cellusys CodeCamp – Puzzles Challenge Assessment"). They are **private**
(unshared), so they cannot be downloaded programmatically — the app resolves
them to files in this folder instead.

## How to add the images

1. Open the source Google Form (you have edit access).
2. For each image, download the picture the form uses for that question/option.
3. Save it into this folder named exactly: `<drive_id>.<ext>`
   (any extension works, e.g. `.png`, `.jpg`).
4. Run the import script to re-resolve the filenames:
   `\.venv\Scripts\python.exe -m scripts.import_puzzles`

Questions/options whose image is missing simply render with no image — the test
still works, so this does not block the rollout.

## Required files (drive id → filename)

Below is every image used by the quiz, keyed by its Google Drive file id (which
is the required filename without the extension).

### Question-level images
```
1xhTvkgskZ-7vinRFG9zjigv7-Keh4M3ghvcAk0AwFGgh474   Q3  "1. What is shown in the image?"
1qi8LJXoQM0A9nIh6ygJnWqTIjlYu_pryXPcVA4ryLo-GUuo   Q4  "2. What is shown in the image?"
1wamb2kRhJ9Mxh5M-jgH6Zn-4wnmQs3NrC4WeufQJQpXsrI8   Q5  logic mistake
1KxyF9Q4VtU3aYZ1YxN4YKvIiqaDGghZQgGjckYVgyCUPhX4   Q6  grid instructions
17obznLfuFa-AdE6E-XaH6XLULUj5BVUStHM7KM-32KfdULk   Q7  combine two pieces
1XRoKYXdx3DCW03r7NdtcDeMZxQNA3nWuuTRlcWFW0kNldSk   Q8  missing piece pattern
1mPPzmZKbBzhSeRa6OuNo44nj5uRMzLxXBwjxpZfDMz9KesI   Q9  fit final space
1cmPQLLrvJofkjo0VC6wZL-tE200W5Cm5eA07S3ScvBQU1eI   Q10 missing letter pattern
1JptiYwiyFzxsaVf2P6PnLlP8Z6jQOxphMmRN4uZZBOKuQfU   Q11 farmer sheep
1Mt7qbAOK8CyUBFDxdr1_CjiUTIR3bfLHofgGjLrMUvdIxGI   Q12 expression
1wRNrNDwUSj6VKV4-qMkp9_ZNAkyb2oXcyjwzpFPyp3G-fZA   Q14 triangle angles
13BsZ0LxEJLzdL5xADfG9rglwp63yA6_sIvFrIluAzFzAlX0   Q15 largest area
1-ZK2oI3iknFq_toykNabhTaZh4ZnTy-5rLrw_qyPiMO3_r0   Q16 longest perimeter
1liKcm6V2x2fHPhlM22vd1zKYBp6zRBVG43i67O5B2d2wUn0   Q17 jars probability
12NQGHzUXj-112xajyzjuBuGyHLBTHeRzROVPg_9C8R9LPEI   Q18 dice roll
1mVojO26GhAnQfmZ7OGF9rUijQ0rXk81KSqZOVVhMqYFE6aA   Q19 eggs pyramid
1sQAKS1xAInw2afzGC8S4r7SCoZWx2WgNN47ROvz0ptYOWIw   Q20 how many digits
1PodqPnWUFXkK7BKoQcP3ejHw-AUxVWtruVcNTGVGGI3BQBc   Q21 summations
1RzHLMKMZTCCy1otfrBNNfcdr80Cg7z2xnKCSEzvmAl-hGhU   Q22 3D top view
```

### Option-level images
```
# Q1 Which one is different from the others?
1s3JGwmxRlVuftghK4vuZns7KHzdbvdFWa9AVeCtunA--muc   Potato
1eM5jgtD0ke45rafg-ku1gvHiSaOg2YAdUZbNx5EAOZCwXjo   Pot
1adDg1dNO7Q1rKQagvJeuLE_EI8q4RqPM_RMfFcJDKSzx0d8   Tomato
1ckigMNvfdE17MBpcbPTsixfsrVFGneyC3VleA2CTxycbcdM   Green Pepper

# Q2 Which one is different?
15vQNdvrVg2-_OuysIxQP8FW7A1xzOhnm3Smfaiu6EYA2q-k   Steel
1WMZn81b2-OmsL9iLJnCEQiu7CH7e-Or_W_l8xkXInctdbSg   Copper
1COi3jaPNxmy9zZ26HgYjWbB7IWUTVbn25DOTRplr-f4KZ_I   Wood
1QnulguMD2UTDej74QODGfwzrRSRaP7mYx6lXaA6H5qtDi5A   Aluminium

# Q8 Which piece is missing from the pattern?
1tb4t599eHD6necEwuT-wVhaIgpn68eREVb9-vItWnpKbWqI   A
1e6w6m6tEc0Zzn5Y38lHOqKyQ5Q3eZpQfaot61Hhivb6ABxg   B
1qQhcD4qbN047dbPFxQda5742lVljj09kl1Uh-ljO_MQHgrA   C
1F72JVnE654o9sFBCu5T2CVbLkZ0l4xcmfFLB0m-8aXkdJxE   D
1v9zxLn4ciqVFXOsrcX5MQ9v3BkIRSEt8JYUr7Z_7j6vuE-A   E
1qNekr-bHIJMBa-hp7v1IZND-fxZjdENn8yAbnjICpxcX-qs   F

# Q9 Choose the option to fit the final space
1W8_HjvqadxM9H0UBr-tRVW2t4OC4z0Qd7VPH7clUVmtzy7Y   A
1eYQV5X3sv43ZNSUI7vHkgLKcAiK5ewXnblYQ2JeovhLp4oQ   B
1bpD3-_ZXTseGX22wr4BccXnDpEGb9tNytCz4i7jQNmrb1Xo   C
1E8hFxd7OvWfYUA3ctAXxePpesgkt6mAMac1zBBVGfexXL4g   D
1Kq-Kri6KU1YNUcwaGvsGlYKstnAMTMajKrK0kURLG0Oddec   E
1FPepwRd4UOcDfXv2bFshT_QwHWO89cTchxHCF5XA-yb0UB8   F
1mocsSf2QICrRqtidyjGX3J0bfl0784pnDns9E875yC7mW_c   G
1KmQHxmiDCbQRaqAGlIUr76wdZYx5s2D5ypfoIDPr9mnn4iU   H

# Q22 3D top view options
1MyKNLOInwP3Toy1Z_IwGM3BLU6fWk6WeYh42sVlFgyZA5NQ   A
1IveGwXVxQMKKfzXBrbNlmwChDvREqbHd_bo7RxjcN721HCM   B
10xuASBr5PcTRq1FstCcHhYLFohjrooRVvfvj6IRMx-Le3dU   C
1ILYKYOm9268DR689rrihUgfEWNB7uqofbaua2uwj-wwgsa0   D
```
