import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const trips = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/trips' }),
  schema: ({ image }) =>
    z.object({
      title: z.string(),
      coordLabel: z.string(),
      badge: z.string(),
      status: z.enum(['proximo', 'cupo-lleno', 'pasado']),
      dateLabel: z.string(),
      durationLabel: z.string(),
      includesLabel: z.string(),
      priceLabel: z.string(),
      capacityLabel: z.string(),
      includes: z.array(z.string()),
      coverImage: image(),
      coverAlt: z.string(),
      coverCaption: z.string(),
      order: z.number().default(0),
    }),
});

export const collections = { trips };
