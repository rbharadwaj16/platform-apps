import { createBackendModule } from '@backstage/backend-plugin-api';
import { scaffolderActionsExtensionPoint } from '@backstage/plugin-scaffolder-node';
import { createTemplateAction } from '@backstage/plugin-scaffolder-node';

type TranslatorResponse = {
  resource_type: string;
  parameters: {
    storageAccountName?: string;
    resourceGroupName?: string;
    location?: string;
    sku?: string;
    clusterName?: string;
    defaultNodePoolVmSize?: string;
    defaultNodePoolNodeCount?: number;
    localAccountDisabled?: boolean;
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
              'Call translator service and return extracted infrastructure parameters',
            schema: {
              input: {
                requestText: z => z.string(),
                expectedResourceType: z => z.string().optional(),
              },
              output: {
                resource_type: z => z.string(),
                parameters: z =>
                  z.object({
                    storageAccountName: z.string().optional(),
                    resourceGroupName: z.string().optional(),
                    location: z.string().optional(),
                    sku: z.string().optional(),
                    clusterName: z.string().optional(),
                    defaultNodePoolVmSize: z.string().optional(),
                    defaultNodePoolNodeCount: z.number().optional(),
                    localAccountDisabled: z.boolean().optional(),
                  }),
                missing_fields: z => z.array(z.string()),
                needs_clarification: z => z.boolean(),
              },
            },
            async handler(ctx) {
              const translatorUrl =
                process.env.TRANSLATOR_SERVICE_URL ??
                'http://localhost:8000/translate';

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

              if (
                ctx.input.expectedResourceType &&
                data.translation.resource_type !== ctx.input.expectedResourceType
              ) {
                throw new Error(
                  `Translator returned resource type '${data.translation.resource_type}', expected '${ctx.input.expectedResourceType}'`,
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
