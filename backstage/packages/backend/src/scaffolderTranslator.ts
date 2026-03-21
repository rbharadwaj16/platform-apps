import { createBackendModule } from '@backstage/backend-plugin-api';
import { scaffolderActionsExtensionPoint } from '@backstage/plugin-scaffolder-node';
import { createTemplateAction } from '@backstage/plugin-scaffolder-node';
import { z } from 'zod';

type TranslatorResponse = {
  resource_type: string;
  parameters: {
    storageAccountName?: string;
    resourceGroupName?: string;
    location?: string;
    sku?: string;
  };
  missing_fields: string[];
  needs_clarification: boolean;
};

export const scaffolderTranslatorModule = createBackendModule({
  pluginId: 'scaffolder',
  moduleId: 'translator-action',
  register(env) {
    env.registerInit({
      deps: {
        scaffolder: scaffolderActionsExtensionPoint,
      },
      async init({ scaffolder }) {
        scaffolder.addActions(
          createTemplateAction({
            id: 'ace:translator:run',
            description:
              'Call translator service and return extracted storage account parameters',
            schema: {
              input: z.object({
                requestText: z.string(),
              }),
              output: z.object({
                resource_type: z.string(),
                parameters: z.object({
                  storageAccountName: z.string().optional(),
                  resourceGroupName: z.string().optional(),
                  location: z.string().optional(),
                  sku: z.string().optional(),
                }),
                missing_fields: z.array(z.string()),
                needs_clarification: z.boolean(),
              }),
            },
            async handler(ctx) {
              const translatorUrl = 'http://localhost:8000/translate';

              const response = await fetch(translatorUrl, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                  request: ctx.input.requestText,
                }),
              });

              if (!response.ok) {
                const errorText = await response.text();
                throw new Error(
                  `Translator service failed: ${response.status} ${response.statusText} - ${errorText}`,
                );
              }

              const data = (await response.json()) as {
                translation?: TranslatorResponse;
                errors?: string[];
              };

              if (!data.translation) {
                throw new Error(
                  `Translator did not return translation. Errors: ${JSON.stringify(
                    data.errors ?? [],
                  )}`,
                );
              }

              if (data.translation.needs_clarification) {
                throw new Error(
                  `Translator needs clarification. Missing fields: ${data.translation.missing_fields.join(
                    ', ',
                  )}`,
                );
              }

              ctx.output('resource_type', data.translation.resource_type);
              ctx.output('parameters', data.translation.parameters);
              ctx.output('missing_fields', data.translation.missing_fields);
              ctx.output(
                'needs_clarification',
                data.translation.needs_clarification,
              );
            },
          }),
        );
      },
    });
  },
});