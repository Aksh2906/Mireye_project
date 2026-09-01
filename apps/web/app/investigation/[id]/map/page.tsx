import DecisionIntelligenceView from "@/components/DecisionIntelligenceView";
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DecisionIntelligenceView id={id} resource="map" />;
}
