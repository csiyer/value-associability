
calculate_mem = function(dat){
FIXATION = 0
TARGET = 1
REPEAT = 2
FILLER = 3
VIGILANCE = 4

HIT = 11
MISS = 12
FALSEALARM = 13
CORRECTREJECTION = 14

TargetHit = 211
TargetFA = 113
TargetMiss = 212
FillerHit = 411
FillerFA = 313
FillerMiss = 412
TCorrectRej = 114
FCorrectRej = 314

summary(dat)

# convert original data to all of the response + image type for all participants
# row = response, column = participant
# name the outcome of trials based on the number code above
dat.trans = matrix(, nrow = 410, ncol = nrow(dat))
for (i in 1:nrow(dat)) {
  dat.1 = as.numeric(strsplit(dat$Answer.perfseq[i], split = ',' )[[1]])
  dat.1.i = as.numeric(strsplit(dat$Answer.imtypeseq[i], split = ',' )[[1]])*100
  mem.dat1 = dat.1+dat.1.i
  dat.trans[,i] = mem.dat1 
}
dat.trans = data.frame(dat.trans)

#count number of response
levels=unique(do.call(c,dat.trans)) #all unique values (image names) in data
response.frequency = sapply(levels,function(x)colSums(dat.trans==x)) #count occurrences of each unique image names in each row
colnames(response.frequency) = levels


#transform the response in fixation
dat.trans.orig = matrix(, nrow = 410, ncol = nrow(dat))
for (i in 1:nrow(dat)) {
  dat.1.i = as.numeric(strsplit(dat$Answer.imtypeseq[i], split = ',' )[[1]])
  mem.dat1 = dat.1.i
  dat.trans.orig[,i] = mem.dat1 
}

dat.trans.orig = dat.trans.orig[seq(1,nrow(dat.trans.orig),2), ]
dat.trans.image = dat.trans[seq(1,nrow(dat.trans),2), ]
dat.trans.fixation = dat.trans[seq(2,nrow(dat.trans),2), ]
dat.trans.perf = dat.trans.image

for (i in 1:nrow(dat.trans.image)) {
  for (j in 1:ncol(dat.trans.image)){
    if (dat.trans.fixation[i,j] != 0){
      dat.trans.perf[i,j] = dat.trans.orig[i,j]*100 + dat.trans.fixation[i,j]
    }
  }
}

# tabeling for dat.trans.perf (corrected hit)
levels=unique(do.call(c,dat.trans.perf)) #all unique values in df
response.frequency.add = sapply(levels,function(x)colSums(dat.trans.perf==x)) #count occurrences of x in each row
colnames(response.frequency.add) = levels
table(dat.trans.orig)

# rename columns
# response.frequency.add is the fixation corrected version of response.frequency
colnames(response.frequency.add)[colnames(response.frequency.add) == as.character(TargetHit)] = "TargetHit"
colnames(response.frequency.add)[colnames(response.frequency.add) == as.character(TargetFA)] = "TargetFA"
colnames(response.frequency.add)[colnames(response.frequency.add) == as.character(TCorrectRej)] = "TCorrectRej"
colnames(response.frequency.add)[colnames(response.frequency.add) == as.character(FillerHit)] = "FillerHit"
colnames(response.frequency.add)[colnames(response.frequency.add) == as.character(FillerFA)] = "FillerFA"
colnames(response.frequency.add)[colnames(response.frequency.add) == as.character(FCorrectRej)] = "FCorrectRej"
colnames(response.frequency.add)[colnames(response.frequency.add) == as.character(FIXATION)] = "Fixation"
colnames(response.frequency.add)[colnames(response.frequency.add) == as.character(TargetMiss)] = "TargetMiss"
colnames(response.frequency.add)[colnames(response.frequency.add) == as.character(FillerMiss)] = "FillerMiss"
response.frequency.add = response.frequency.add[,order(colnames(response.frequency.add))]


# calculating rate
response.frequency.add = data.frame(response.frequency.add)
response.freq.add.rate = response.frequency.add %>% mutate(THitRate = TargetHit/29,
                                                           TFalseARate = TargetFA/(TargetFA+TargetHit),
                                                           FHitRate = FillerHit/40,
                                                           FFalseARate = FillerFA/(FillerFA+FillerHit))

response.freq.add.rate = response.freq.add.rate %>% mutate(keyPress = FillerFA+FillerHit+TargetFA+TargetHit, 
                                                           HitTotal = TargetHit+FillerHit, 
                                                           CRTotal = TCorrectRej + FCorrectRej)

dat.img = matrix(0, nrow = 410, ncol = nrow(dat))
for (i in 1:nrow(dat)) {
  dat.1 = str_split(dat$Answer.imseq[i], ",", simplify = TRUE )
  dat.img[,i] = dat.1 
}

# transform to 205 image strings for each participant
dat.img = data.frame(dat.img[seq(1,nrow(dat.img),2), ])
labels = union(dat.img[,1], dat.img[,2])

# creating empty target dataframe with image names
img.target.count = as.data.frame( matrix(0, 1, ncol = length(labels)))
colnames(img.target.count) = labels
img.target.hit = img.target.count
img.HR = img.target.count
img.target.FA = img.target.count
img.target.CR = img.target.count

# count the times of the image being an target
for (i in 1:nrow(dat.img)){
  for (j in 1:ncol(dat.img)){
    if (dat.trans.orig[i,j] == TARGET){
      target.name = dat.img[i,j]
      img.target.count[1,target.name] = img.target.count[1,target.name]+1
    }
  }
}

# count the Hit times of the image while it's a target
for (i in 1:nrow(dat.img)){
  for (j in 1:ncol(dat.img)){
    if (dat.trans.perf[i,j] == TargetHit){
      target.hit.name = dat.img[i,j]
      img.target.hit[1,target.hit.name] = img.target.hit[1,target.hit.name]+1
    }
  }
}


# calculating FAR
# count the time of a target image being FA
for (i in 1:nrow(dat.img)){
  for (j in 1:ncol(dat.img)){
    if (dat.trans.perf[i,j] == TargetFA){
      target.FA.name = dat.img[i,j]
      img.target.FA[1,target.FA.name] = img.target.FA[1,target.FA.name]+1
    }
  }
}

# count correct rej for target
for (i in 1:nrow(dat.img)){
  for (j in 1:ncol(dat.img)){
    if (dat.trans.perf[i,j] == TCorrectRej){
      target.hit.name = dat.img[i,j]
      img.target.CR[1,target.hit.name] = img.target.CR[1,target.hit.name]+1
    }
  }
}

# count HR and FAR for each image
img.HR = img.target.hit/img.target.count
img.TargetFAR = img.target.FA/(img.target.FA+img.target.CR)

# memorability = HR-FAR
img.mem = img.HR - img.TargetFAR

# output together
img.values = img.target.count
img.values[2,] = img.target.hit
img.values[3,] = img.target.FA
img.values[4,] = img.HR
img.values[5,] = img.TargetFAR
img.values[6,] = img.mem

rownames(img.values) = c("Target.count", "Hit.count", "FA.count", "HR", "FAR", "Memorability")
img.values = data.frame(t(img.values))
img.values$image = rownames(img.values)
return(img.values)
}

#write.csv(img.values, "output/all_mem_values_manuscript.csv")

