// Writes frontend/.oxlintrc.json: the import boundaries between frontend layers
// (docs/architecture/frontend.md). An override's `no-restricted-imports` replaces the
// rule's options rather than adding to them, so the JSON repeats every pattern in each
// override; here each one is written once. Edit this file, not the JSON.
import { writeFileSync } from 'node:fs';

const noGeneratedTypes = {
  group: ['**/api.generated'],
  message: 'Backend shapes come from shared/types/api.ts, which names each one.',
};
const typesFromIndex = {
  group: ['**/shared/types/*'],
  message: "Import shared types from '@/shared/types', not a single file in it.",
};
const featureThroughIndex = {
  group: ['**/features/*/**'],
  message: "Use another feature only through its public API ('@/features/<name>'), never a file inside it.",
};
const chatOnlyFromChatPage = {
  group: ['**/features/chat'],
  message:
    'Only the lazily loaded pages/ChatPage and pages/SharedChatPage import the chat feature: it pulls in the markdown renderer.',
};
const leaveFeatureByAlias = (relative) => ({
  group: [relative],
  message: "Leave a feature only through '@/…' imports, so a reach into another feature's files is caught.",
});
const presentNoApi = {
  group: ['**/api/**'],
  message: 'Components and pages only present: reach the server through a hook or context.',
};
const presentNoQuery = {
  group: ['@tanstack/react-query'],
  message: "Components and pages only present: server data comes through a feature's hook.",
};
const logicNoPresentation = {
  group: ['**/components/**', '**/pages/**', '**/shared/ui/**'],
  message: "Hooks and context are the logic layer: they don't render or depend on presentation.",
};
const apiOnlyBackend = {
  group: ['**/hooks/**', '**/context/**', '**/components/**', '**/pages/**', '**/shared/ui/**', '**/features/**'],
  message: 'api/ only talks to the backend: no framework state, no presentation, no other feature.',
};
const modelIsPure = {
  group: [
    '**/api/**',
    '**/hooks/**',
    '**/context/**',
    '**/components/**',
    '**/pages/**',
    '**/shared/ui/**',
    '**/shared/hooks/**',
  ],
  message: 'model/ is pure helpers: no network, no framework state, no presentation.',
};
const sharedIsLeaf = {
  group: ['**/features/**', '**/pages/**', '**/app/**'],
  message: 'shared/ is used by features, never the other way round.',
};

// What every file in src/ obeys outside shared/, and inside it.
const app = [noGeneratedTypes, typesFromIndex, featureThroughIndex, chatOnlyFromChatPage];
const shared = [noGeneratedTypes, typesFromIndex, sharedIsLeaf];
const insideFeature = [...app, leaveFeatureByAlias('../../**')];

const restrict = (patterns, paths) => ({
  'no-restricted-imports': ['error', paths ? { patterns, paths } : { patterns }],
});

const config = {
  $schema: './node_modules/oxlint/configuration_schema.json',
  plugins: ['react', 'typescript', 'oxc'],
  rules: {
    'react/rules-of-hooks': 'error',
    'react/only-export-components': ['warn', { allowConstantExport: true }],
    'no-restricted-globals': [
      'error',
      {
        name: 'fetch',
        message:
          'Call the backend through shared/api/client.ts (request, requestJson, authFetch): it adds the token and refreshes it.',
      },
    ],
    ...restrict(app),
  },
  overrides: [
    {
      files: ['src/shared/api/client.ts', 'src/features/auth/api/auth.ts'],
      rules: { 'no-restricted-globals': 'off' },
    },
    { files: ['src/features/*/*.ts'], rules: restrict([...app, leaveFeatureByAlias('../**')]) },
    {
      files: ['src/features/*/components/**'],
      rules: restrict([...insideFeature, presentNoApi, presentNoQuery]),
    },
    {
      files: ['src/features/*/hooks/**', 'src/features/*/context/**'],
      rules: restrict([...insideFeature, logicNoPresentation]),
    },
    {
      files: ['src/features/*/api/**'],
      rules: restrict(
        [...insideFeature, apiOnlyBackend],
        [
          {
            name: '@/shared/api/client',
            importNames: ['authFetch', 'apiUrl', 'jsonPostInit'],
            message:
              'Call the backend through the typed `api` client (with `unwrap`), checked against the OpenAPI schema. Only the SSE stream, the multipart upload and login need the untyped calls.',
          },
        ]
      ),
    },
    {
      // The untyped calls: the SSE stream, the multipart upload and login.
      files: [
        'src/features/chat/api/chat.ts',
        'src/features/knowledge-base/api/ingestions.ts',
        'src/features/auth/api/auth.ts',
      ],
      rules: restrict([...insideFeature, apiOnlyBackend]),
    },
    { files: ['src/features/*/model/**'], rules: restrict([...insideFeature, modelIsPure]) },
    { files: ['src/app/**'], rules: restrict([...app, presentNoApi]) },
    { files: ['src/app/App.tsx'], rules: restrict(app) },
    { files: ['src/pages/**'], rules: restrict([...app, presentNoApi, presentNoQuery]) },
    {
      files: ['src/pages/ChatPage.tsx', 'src/pages/SharedChatPage.tsx'],
      rules: restrict([
        ...app.filter((pattern) => pattern !== chatOnlyFromChatPage),
        presentNoApi,
        presentNoQuery,
      ]),
    },
    { files: ['src/shared/ui/**'], rules: restrict([...shared, presentNoApi, presentNoQuery]) },
    { files: ['src/shared/hooks/**'], rules: restrict([...shared, logicNoPresentation]) },
    { files: ['src/shared/api/**'], rules: restrict([...shared, apiOnlyBackend]) },
    { files: ['src/shared/types/api.ts'], rules: { 'no-restricted-imports': 'off' } },
    { files: ['tests/**'], rules: restrict([noGeneratedTypes]) },
  ],
};

writeFileSync(new URL('../frontend/.oxlintrc.json', import.meta.url), `${JSON.stringify(config, null, 2)}\n`);
