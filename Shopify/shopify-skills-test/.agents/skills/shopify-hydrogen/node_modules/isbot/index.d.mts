declare function getPattern(): RegExp;
/**
 * A list of bot identifiers to be used in a regular expression against user agent strings.
 */
declare const list: string[];
/**
 * Check if the given user agent includes a bot pattern.
 */
declare function isbot(userAgent?: string | null): boolean;
/**
 * Check if the given user agent includes a bot pattern. Naive implementation (less accurate).
 */
declare const isbotNaive: typeof isbot;
/**
 * Create a custom isbot function with a custom pattern.
 */
declare const createIsbot: (customPattern: RegExp) => typeof isbot;
/**
 * Create a custom isbot function with a custom pattern.
 */
declare const createIsbotFromList: (list: string[]) => typeof isbot;
/**
 * Find the first part of the user agent that matches a bot pattern.
 */
declare const isbotMatch: (userAgent: Parameters<typeof isbot>[0]) => string | null;
/**
 * Find all parts of the user agent that match a bot pattern.
 */
declare const isbotMatches: (userAgent: Parameters<typeof isbot>[0]) => string[];
/**
 * Find the first bot pattern that match the given user agent.
 */
declare const isbotPattern: (userAgent: Parameters<typeof isbot>[0]) => string | null;
/**
 * Find all bot patterns that match the given user agent.
 */
declare const isbotPatterns: (userAgent: Parameters<typeof isbot>[0]) => string[];

export { createIsbot, createIsbotFromList, getPattern, isbot, isbotMatch, isbotMatches, isbotNaive, isbotPattern, isbotPatterns, list };
