library(tidyverse)

base_dir <- '~/Documents/GitHub/value-associability/pilot/duncan_shohamy'
data_path <- file.path(base_dir, 'raw_by_subject')

filepaths <- list.files(path = data_path,
                        full.names = TRUE)

# Col1: Value of the old object (0, 0.2, 0.4, 0.6, 0.8 or 1)
# Col2: chose old=1, did not choose old = 0
# Col3: Reaction time in seconds
# Col4: Familiarity (1 = shown on the same background as first time, 0 = shown on a different background than first time item is seen)
# Col5: Delay (continuous, number of trials since old item seen for the first time)
# Col6: Encoding scene new (1 = background when the old item was seen for the first time was new i.e. background was never seen before encoding of the old item, 0 = the background when the old item was seen for the first time was old and had been experience before then)

duncan_shohamy_df <- read_csv(filepaths, 
                              col_names = c('old_value', 'chose_old', 'rt', 'familiarity', 'delay', 'encoding_familiarity'),
                              id = "file")

duncan_shohamy_df <- duncan_shohamy_df |>
  mutate(
    subject = str_extract(file, "\\d+"),
    optimal_choice = if_else(old_value > .5, chose_old, (1 - chose_old))
  )

value_sub_df <- duncan_shohamy_df |>
  filter(delay >= 7, delay <= 15) |>
  group_by(subject, old_value) |>
  summarize(
    p_chose_old = mean(chose_old)
  )
value_sub_df |>
  ggplot(aes(old_value, p_chose_old)) +
  stat_summary() +
  stat_summary(geom = 'line') +
  theme_classic() +
  labs(x = "Old Item Value", y = "P(Chose Old)")

delay_sub_df <- duncan_shohamy_df |>
  group_by(subject, delay) |>
  summarize(
    p_optimal_choice = mean(optimal_choice)
  )

delay_sub_df |>
  filter(delay >= 7, delay <= 15) |>
  ggplot(aes(delay, p_optimal_choice)) +
  stat_summary() +
  stat_summary(geom = 'line') +
  theme_classic()

familiarity_value_sub_df <- duncan_shohamy_df |>
  group_by(subject, familiarity, old_value) |>
  summarize(p_chose_old = mean(chose_old))
familiarity_value_sub_df |> 
  ggplot(aes(old_value, p_chose_old, color = factor(familiarity), group = factor(familiarity))) + 
  stat_summary()
