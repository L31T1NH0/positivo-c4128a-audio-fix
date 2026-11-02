int main(void) {
 struct regmap map = {0};
 struct snd_soc_jack jack = {.status = SND_JACK_MICROPHONE};
 struct es8326_priv state = {.regmap = &map, .jack = &jack};
 struct snd_soc_component component = {.data = &state};
 struct snd_kcontrol control = {.chip = &component};
 struct snd_ctl_elem_value value = {0};
 value.value.integer.value[0] = 1;
 assert(es8326_internal_dmic_put(&control, &value) == 1);
 assert(state.force_internal_dmic && map.left == 0x44 && map.right == 0x66 && state.lock == 0);
 assert(es8326_internal_dmic_get(&control, &value) == 0 && value.value.integer.value[0] == 1);
 mutex_lock(&state.lock);
 assert(es8326_apply_adc_sources(&state, 0, 0) == 0);
 mutex_unlock(&state.lock);
 assert(map.left == 0x44 && map.right == 0x66);
 assert(es8326_internal_dmic_put(&control, &value) == 0);
 value.value.integer.value[0] = 0;
 assert(es8326_internal_dmic_put(&control, &value) == 1);
 assert(!state.force_internal_dmic && map.left == 0 && map.right == 0);
 jack.status = 0;
 assert(es8326_internal_dmic_put(&control, &value) == 0);
 assert(map.left == 0x44 && map.right == 0x66);
 for (long invalid = -1; invalid <= 2; invalid += 3) {
  value.value.integer.value[0] = invalid;
  assert(es8326_internal_dmic_put(&control, &value) == -EINVAL);
  assert(!state.force_internal_dmic && state.lock == 0);
 }
 map.fail = true; value.value.integer.value[0] = 1;
 assert(es8326_internal_dmic_put(&control, &value) == -EIO);
 assert(!state.force_internal_dmic && state.lock == 0);
 map.fail = false; state.jack = NULL; value.value.integer.value[0] = 0;
 assert(es8326_internal_dmic_put(&control, &value) == 0);
 assert(map.left == 0x44 && map.right == 0x66);
 puts("OK: controle, reescrita de jack, modo automático, valores inválidos e erro I2C.");
 return 0;
}
