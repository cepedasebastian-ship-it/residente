import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const trips = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/trips' }),
  schema: ({ image }) =>
    z.object({
      title: z.string(),
      navLabel: z.string(),
      coordLabel: z.string(),
      badge: z.string(),
      status: z.enum(['proximo', 'cupo-lleno', 'pasado']),
      dateLabel: z.string(),
      durationLabel: z.string(),
      includesLabel: z.string(),
      priceLabel: z.string(),
      capacityLabel: z.string(),
      capacityTotal: z.number().optional(),
      spotsTaken: z.number().optional(),
      includes: z.array(z.string()),
      coverImage: image(),
      coverAlt: z.string(),
      coverCaption: z.string(),
      gallery: z
        .array(z.object({ photo: image(), caption: z.string().optional().default('') }))
        .optional()
        .default([]),
      itinerary: z
        .array(z.object({ day: z.string(), title: z.string(), description: z.string() }))
        .optional()
        .default([]),
      order: z.number().default(0),
    }),
});

const posts = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/posts' }),
  schema: ({ image }) =>
    z.object({
      title: z.string(),
      date: z.string(),
      excerpt: z.string(),
      coverImage: image(),
      coverAlt: z.string(),
    }),
});

export const collections = { trips, posts };
