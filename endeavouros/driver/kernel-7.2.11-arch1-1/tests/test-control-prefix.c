#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <errno.h>
#define ES8326_ADC1_SRC 0x2a
#define ES8326_ADC2_SRC 0x2b
#define SND_JACK_MICROPHONE 2
#define ARRAY_SIZE(x) (sizeof(x) / sizeof((x)[0]))
struct reg_sequence { unsigned int reg, def; };
struct regmap { bool fail; unsigned int left, right; };
struct snd_soc_jack { int status; };
struct es8326_priv { bool force_internal_dmic; struct regmap *regmap; int lock; struct snd_soc_jack *jack; };
struct snd_soc_component { struct es8326_priv *data; };
struct snd_kcontrol { struct snd_soc_component *chip; };
struct snd_ctl_elem_value { struct { struct { long value[1]; } integer; } value; };
static struct snd_soc_component *snd_kcontrol_chip(struct snd_kcontrol *k) { return k->chip; }
static struct es8326_priv *snd_soc_component_get_drvdata(struct snd_soc_component *c) { return c->data; }
static void mutex_lock(int *m) { assert(*m == 0); *m = 1; }
static void mutex_unlock(int *m) { assert(*m == 1); *m = 0; }
static int regmap_multi_reg_write(struct regmap *m, const struct reg_sequence *s, unsigned int n) {
 assert(n == 2 && s[0].reg == 0x2a && s[1].reg == 0x2b);
 if (m->fail) return -EIO;
 m->left = s[0].def; m->right = s[1].def; return 0;
}
