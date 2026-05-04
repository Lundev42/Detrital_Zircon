# RiktigRekkefølge.R
#
# Calls detzrcr's plot_dens_hist() exactly as it lives in plotting.R, with
# only these adjustments:
#   1. sample order is taken from Alle_ZirkonPrøver_rekkefølge.csv (set via
#      factor levels — same trick the detzrcr Shiny app uses).
#   2. x-axis breaks tweaked per plot.
#   3. plot_text_options() applied so labels match the Shiny output size.
#   4. samples are split into two groups (Group 1 = first 3, Group 2 = last
#      7); the two groups are stacked with a 2 cm gap via patchwork so each
#      group reads as its own complete plot (own bottom x-axis, own "Count"
#      y-label).
#
# Produces two figures:
#   AllePrøver  (480-3100 Ma, bin=50, bw=30, 15x30 cm)
#   YngstePrøver (480-750 Ma,  bin=10, bw=5,  10x30 cm)
#
# For YngstePrøver the data is filtered to 480-750 BEFORE plot_dens_hist,
# because detzrcr's calc_dens_hist scales the KDE by the global histogram
# max (full 0-4560 range). Without the pre-filter the KDE in 480-750 gets
# scaled to the much taller 1000 Ma peak and floats above the bars.
#
# Run: Rscript RiktigRekkefølge.R   (or source() in RStudio)

suppressPackageStartupMessages({
  library(detzrcr)
  library(ggplot2)
  library(patchwork)
})

PROJECT_DIR <- "C:/Users/vetle/Detrital_Zirkon"
CSV_PATH    <- file.path(PROJECT_DIR, "Alle_ZirkonPrøver_rekkefølge.csv")
OUTPUT_DIR  <- "C:/Users/vetle/OneDrive - Høgskulen på Vestlandet/7. Bachelor/Zirkondatering"
OUTPUT_PREFIX <- "Claude"

SAMPLE_ORDER <- c("163706", "EM28", "SK25-2",
                  "DG12", "AK_121", "119037", "GM34",
                  "DG27", "DGA14_MN_121", "AK001")
GROUP_1 <- SAMPLE_ORDER[1:3]
GROUP_2 <- SAMPLE_ORDER[4:10]

GAP_CM <- 0.0

# --- read CSV --------------------------------------------------------------
dat <- read.csv(CSV_PATH, sep = ";", stringsAsFactors = FALSE,
                fileEncoding = "UTF-8")
names(dat) <- tolower(trimws(names(dat)))
age_col <- grep("^age", names(dat), value = TRUE)[1]
dat$age <- suppressWarnings(as.numeric(gsub(",", ".", as.character(dat[[age_col]]))))
dat$sample <- trimws(as.character(dat$sample))
dat <- dat[!is.na(dat$age) & dat$sample %in% SAMPLE_ORDER, c("sample", "age")]

missing <- setdiff(SAMPLE_ORDER, unique(dat$sample))
if (length(missing) > 0) stop("Missing samples in CSV: ",
                              paste(missing, collapse = ", "))

# --- age-group classification ---------------------------------------------
# Bars are coloured by the age group each grain falls in. Ages outside the
# three named groups (e.g. 750-900 Ma, 2100-2400 Ma) keep detzrcr's default
# grey60 fill so the figure still reads as a continuous histogram.
AGE_COLORS <- c(
  archean      = "#CC8181",
  paleo_meso   = "#6895C1",
  neo_cambrian = "#7EBC8E",
  other        = "grey60"
)

dat$age_group <- ifelse(dat$age > 2400, "archean",
                 ifelse(dat$age >= 900 & dat$age <= 2100, "paleo_meso",
                 ifelse(dat$age >= 480 & dat$age <= 750, "neo_cambrian", "other")))

# --- shared label settings -------------------------------------------------
text_opts <- plot_text_options(
  font_name         = "sans",
  title_size        = 13,
  label_size        = 9,
  legend_size       = 10,
  strip_text_y_size = 9
)

# --- helpers ---------------------------------------------------------------
next_index <- function() {
  pat <- paste0("^", OUTPUT_PREFIX, "(\\d+)\\.(pdf|png)$")
  files <- list.files(OUTPUT_DIR, pattern = pat)
  if (length(files) == 0) return(1L)
  max(as.integer(sub(pat, "\\1", files)), na.rm = TRUE) + 1L
}

save_pair <- function(plot_obj, width_cm, height_cm) {
  idx <- next_index()
  pdf_path <- file.path(OUTPUT_DIR, sprintf("%s%d.pdf", OUTPUT_PREFIX, idx))
  png_path <- file.path(OUTPUT_DIR, sprintf("%s%d.png", OUTPUT_PREFIX, idx))
  # Match Shiny's downloadDensplot exactly: cm units, CMYK colormodel.
  ggsave(pdf_path, plot_obj, width = width_cm, height = height_cm,
         units = "cm", colormodel = "cmyk")
  # PNG: cairo device for proper antialiasing on the KDE line and the
  # histogram bar edges (the default Windows png device leaves the KDE
  # looking pixelated and clips a pixel at each bar's top-left corner).
  ggsave(png_path, plot_obj, width = width_cm, height = height_cm,
         units = "cm", dpi = 600, type = "cairo-png", bg = "white")
  cat(sprintf("Saved: %s\n", basename(pdf_path)))
  cat(sprintf("Saved: %s\n", basename(png_path)))
}

# Mirror of detzrcr's plot_dens_hist (see plotting.R) but with the histogram
# fill mapped to age_group via scale_fill_manual instead of the default
# fixed grey60. Density math (calc_dens_hist) and overall layout — facet,
# theme, axes — are unchanged.
plot_dens_hist_grouped <- function(d, binwidth, bw, age_range, fixed_y, step) {
  l <- lapply(split(d, factor(d$sample)), calc_dens_hist, bw = bw,
              binwidth = binwidth, type = "kde", age_range = age_range)
  dens <- do.call(rbind.data.frame, l)

  gplot <- ggplot() +
    geom_histogram(
      data = d,
      aes(x = age, fill = age_group),
      color = "grey90",
      breaks = seq(0, 4560, binwidth),
      na.rm = TRUE
    ) +
    scale_fill_manual(values = AGE_COLORS, guide = "none")

  if (fixed_y) {
    gplot <- gplot + facet_grid(sample ~ .)
  } else {
    gplot <- gplot + facet_grid(sample ~ ., scales = "free_y")
  }

  gplot <- gplot +
    geom_path(data = dens, aes(x = x, y = y), na.rm = TRUE) +
    plot_labels(ylab = "Count") +
    plot_bw_theme() +
    plot_axis_lim(xlim = age_range, step = step)
  gplot
}

# Build a single-group plot. Adds:
#   - factor() so panels are in the requested order
#   - facet_grid(..., drop=FALSE) so empty panels still render (needed for
#     YngstePrøver where some samples have no ages in 480-750)
#   - custom x scale
#   - text_opts
#   - optional fixed y range (used by YngstePrøver to share y across groups)
build_group_plot <- function(group_dat, samples, x_min, x_max, binwidth, bw,
                             breaks_x, fixed_y, ylim_vec = NULL) {
  d <- group_dat[group_dat$sample %in% samples, ]
  d$sample <- factor(d$sample, levels = samples)

  p <- plot_dens_hist_grouped(
    d,
    binwidth  = binwidth,
    bw        = bw,
    age_range = c(x_min, x_max),
    fixed_y   = fixed_y,
    step      = 200          # overridden below by scale_x_continuous
  )

  scales_arg <- if (fixed_y) "fixed" else "free_y"
  p <- suppressMessages(
    p + facet_grid(sample ~ ., scales = scales_arg, drop = FALSE)
  )
  p <- suppressMessages(p + scale_x_continuous(breaks = breaks_x))
  if (!is.null(ylim_vec)) {
    p <- suppressMessages(
      p + coord_cartesian(xlim = c(x_min, x_max), ylim = ylim_vec)
    )
  }
  p + text_opts
}

# Combine two group plots into one figure with a ~2 cm spacer between them.
# Using relative heights (ratios) lets patchwork auto-fit the axes inside
# the requested canvas. The gap ratio is calibrated so the spacer ends up
# roughly 2 cm tall on a 30 cm canvas.
combine_groups <- function(p1, p2, height_cm = 30) {
  panel_cm   <- (height_cm - GAP_CM - 2) / length(SAMPLE_ORDER)  # ~2 cm for axes
  gap_ratio  <- GAP_CM / panel_cm
  p1 / plot_spacer() / p2 +
    plot_layout(heights = c(length(GROUP_1), gap_ratio, length(GROUP_2)))
}

dir.create(OUTPUT_DIR, showWarnings = FALSE, recursive = TRUE)

# --- AllePrøver: 480-3100 Ma, bin 50, bw 30, 15 x 30 cm --------------------
breaks_full <- c(480, seq(700, 3100, 200))
p_alle_g1 <- build_group_plot(dat, GROUP_1, 480, 3100, 50, 30, breaks_full,
                              fixed_y = FALSE) +
  theme(axis.title.x = element_blank())
p_alle_g2 <- build_group_plot(dat, GROUP_2, 480, 3100, 50, 30, breaks_full,
                              fixed_y = FALSE)
save_pair(combine_groups(p_alle_g1, p_alle_g2, height_cm = 30),
          width_cm = 15, height_cm = 30)

# --- YngstePrøver: 480-750 Ma, bin 10, bw 5, 10 x 30 cm --------------------
# Pre-filter so calc_dens_hist scales the KDE against the local 480-750
# histogram max, not the global 0-4560 max.
young_dat <- dat[dat$age >= 480 & dat$age <= 750, ]

# Shared y range so both groups stack with a single matching scale (mirrors
# the unsplit fixed_y YngstePrøver from the previous run).
hist_breaks <- seq(0, 4560, 10)
counts_per_sample <- vapply(SAMPLE_ORDER, function(s) {
  ages <- young_dat$age[young_dat$sample == s]
  if (length(ages) == 0) return(0L)
  max(hist(ages, breaks = hist_breaks, plot = FALSE)$counts)
}, integer(1))
y_max_young <- max(counts_per_sample) * 1.05

breaks_young <- seq(480, 750, 30)
p_young_g1 <- build_group_plot(young_dat, GROUP_1, 480, 750, 10, 5,
                               breaks_young, fixed_y = TRUE,
                               ylim_vec = c(0, y_max_young)) +
  theme(axis.title.x = element_blank())
p_young_g2 <- build_group_plot(young_dat, GROUP_2, 480, 750, 10, 5,
                               breaks_young, fixed_y = TRUE,
                               ylim_vec = c(0, y_max_young))
save_pair(combine_groups(p_young_g1, p_young_g2, height_cm = 30),
          width_cm = 10, height_cm = 30)
