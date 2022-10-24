## CRAN mirror
local({
    r <- getOption("repos")
    r["CRAN"] <- "https://stat.ethz.ch/CRAN/"
    options(repos = r)
})

# syler
options(languageserver.formatting_style = function(options) {
    style <- styler::tidyverse_style(strict = FALSE, indent_by = 4) # indent_b>
    # style$token$force_assignment_op <- NULL
    style$space$set_space_between_eq_sub_and_comma <- NULL
    style
})
