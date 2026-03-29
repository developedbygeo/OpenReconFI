import { SimpleGrid, Card, Skeleton, Stack, Grid } from '@mantine/core'

export function DashboardSkeleton() {
  return (
    <Stack>
      <SimpleGrid cols={{ base: 2, md: 4 }}>
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} withBorder>
            <Skeleton h={12} w="60%" mb="sm" />
            <Skeleton h={28} w="40%" />
          </Card>
        ))}
      </SimpleGrid>

      <Grid>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder>
            <Skeleton h={14} w="40%" mb="md" />
            <Skeleton h={220} />
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder>
            <Skeleton h={14} w="40%" mb="md" />
            <Skeleton h={220} />
          </Card>
        </Grid.Col>
      </Grid>

      <Card withBorder>
        <Skeleton h={14} w="30%" mb="md" />
        <Skeleton h={200} />
      </Card>

      <Grid>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder>
            <Skeleton h={14} w="30%" mb="md" />
            <Skeleton h={100} />
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder>
            <Skeleton h={14} w="40%" mb="md" />
            <Skeleton h={100} />
          </Card>
        </Grid.Col>
      </Grid>
    </Stack>
  )
}
