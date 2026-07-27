rm(list = ls())
setwd("~/Downloads")
dir()

Data <- read.csv("DOK_PZ-FFP_Budg_NUE.txt", sep = "\t")

which(is.na(Data))
colnames(Data)
Data$X

T.BO <- Data[Data$TR.=="BIOORG2",]

T.CF2 <- Data[Data$TR.=="CONFYM2",]

T.CM <- Data[Data$TR.=="CONMIN",]

T.BD <- Data[Data$TR.=="BIODYN2",]

BO.NUE <- vector("list",6)

BD.NUE <- vector("list",6)

CM.NUE <- vector("list",6)

CF2.NUE <- vector("list",6)

for (i in 1:6) {
  
  BO.NUE[[i]] <- (T.BO[T.BO$FFP==i,"NOUT"]-T.BO[T.BO$FFP==i,"SUMNDFA"]+T.BO[T.BO$FFP==i,"SOILNCHANGE"])/T.BO[T.BO$FFP==i,"NINFERT"]
}



for (i in 1:6) {
  
  CF2.NUE[[i]] <- (T.CF2[T.CF2$FFP==i,"NOUT"]-T.CF2[T.CF2$FFP==i,"SUMNDFA"]+T.CF2[T.CF2$FFP==i,"SOILNCHANGE"])/T.CF2[T.CF2$FFP==i,"NINFERT"]
}


for (i in 1:6) {
  
  CM.NUE[[i]] <- (T.CM[T.CM$FFP==i,"NOUT"]-T.CM[T.CM$FFP==i,"SUMNDFA"]+T.CM[T.CM$FFP==i,"SOILNCHANGE"])/T.CM[T.CM$FFP==i,"NINFERT"]
}


for (i in 1:6) {
  
  BD.NUE[[i]] <- (T.BD[T.BD$FFP==i,"NOUT"]-T.BD[T.BD$FFP==i,"SUMNDFA"]+T.BD[T.BD$FFP==i,"SOILNCHANGE"])/T.BD[T.BD$FFP==i,"NINFERT"]
}




lapply(BD.NUE,mean)

t.test(as.numeric(sapply(BO.NUE,mean)),as.numeric(sapply(BD.NUE,mean)))






BO.NUE[1]


lapply(BO.NUE,mean)



