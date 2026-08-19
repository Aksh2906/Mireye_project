import ResourceView from "@/components/ResourceView";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <ResourceView id={id} resource="evidence" title="Evidence provenance" />
  );
}
